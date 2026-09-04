import React, {useEffect, useRef, useState} from 'react';
import {SafeAreaView, View, Text, TextInput, Pressable, ScrollView, StyleSheet, Alert} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const DEFAULT_PORT = '8890';
const STORAGE_KEY = 'jarvis_neo_devices';

export default function App() {
  const [screen, setScreen] = useState('connect');
  const [tab, setTab] = useState('dashboard');
  const [host, setHost] = useState('');
  const [port, setPort] = useState(DEFAULT_PORT);
  const [code, setCode] = useState('');
  const [name, setName] = useState('Mon téléphone');
  const [token, setToken] = useState('');
  const [deviceId, setDeviceId] = useState('');
  const [status, setStatus] = useState('Déconnecté');
  const [system, setSystem] = useState({});
  const [command, setCommand] = useState('');
  const [events, setEvents] = useState([]);
  const ws = useRef(null);
  const reconnectTimer = useRef(null);
  const pingTimer = useRef(null);

  useEffect(() => {
    load();
    return () => closeWS();
  }, []);

  async function load() {
    try {
      const raw = await AsyncStorage.getItem(STORAGE_KEY);
      const devices = raw ? JSON.parse(raw) : [];
      if (devices.length) {
        const d = devices[0];
        setHost(d.host); setPort(d.port || DEFAULT_PORT); setToken(d.token);
        setDeviceId(d.deviceId); setName(d.name || 'Mon téléphone');
        setScreen('home');
        connect(d.host, d.port || DEFAULT_PORT, d.token);
      }
    } catch (e) {
      setEvents(x => [`Impossible de charger les appareils : ${e.message || e}`, ...x]);
    }
  }

  async function save(device) {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    const devices = raw ? JSON.parse(raw) : [];
    const rest = devices.filter(x => x.deviceId !== device.deviceId);
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify([device, ...rest]));
  }

  async function pair() {
    if (!host.trim() || !code.trim()) {
      return Alert.alert('Connexion', "Entre l'adresse IP du PC et le code d'appairage.");
    }
    try {
      const r = await fetch(`http://${host.trim()}:${port}/api/pair`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({code: code.trim(), name: name.trim(), device_id: deviceId || undefined})
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || 'Appairage refusé');
      setToken(data.token); setDeviceId(data.device_id); setScreen('home'); setTab('dashboard');
      await save({host: host.trim(), port, token: data.token, deviceId: data.device_id, name: name.trim()});
      connect(host.trim(), port, data.token);
    } catch (e) {
      Alert.alert('Appairage impossible', String(e.message || e));
    }
  }

  function closeWS() {
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    if (pingTimer.current) clearInterval(pingTimer.current);
    reconnectTimer.current = null; pingTimer.current = null;
    if (ws.current) { try { ws.current.close(); } catch {} ws.current = null; }
  }

  function connect(h = host, p = port, t = token) {
    if (!h || !p || !t) return;
    closeWS();
    setStatus('Connexion…');
    const socket = new WebSocket(`ws://${h}:${p}/ws?token=${encodeURIComponent(t)}`);
    ws.current = socket;

    socket.onopen = () => {
      setStatus('Connecté');
      addEvent('🟢 J.A.R.V.I.S. connecté');
      fetchSystem(h, p, t);
      socket.send(JSON.stringify({type: 'status', token: t, id: `status-${Date.now()}`}));
      pingTimer.current = setInterval(() => {
        if (ws.current?.readyState === 1) {
          ws.current.send(JSON.stringify({type: 'ping', token: t, id: `ping-${Date.now()}`}));
        }
      }, 15000);
    };
    socket.onclose = () => {
      setStatus('Déconnecté');
      if (pingTimer.current) clearInterval(pingTimer.current);
      if (screen === 'home') reconnectTimer.current = setTimeout(() => connect(h, p, t), 2500);
    };
    socket.onerror = () => setStatus('Erreur réseau');
    socket.onmessage = e => {
      try {
        const message = JSON.parse(e.data);
        if (message.type === 'state' || message.type === 'status') {
          const state = message.state || message.payload || {};
          setSystem(state);
          return;
        }
        if (message.type === 'event') {
          const label = message.event ? `${message.event}: ${JSON.stringify(message.payload || {})}` : JSON.stringify(message);
          addEvent(label);
          return;
        }
        if (message.type === 'response' || message.type === 'action_result') {
          addEvent(`↳ ${JSON.stringify(message.result ?? message)}`);
          return;
        }
        if (message.type !== 'pong') addEvent(JSON.stringify(message));
      } catch {
        addEvent(e.data);
      }
    };
  }

  function addEvent(value) {
    setEvents(list => [String(value), ...list].slice(0, 80));
  }

  async function fetchSystem(h = host, p = port, t = token) {
    try {
      const r = await fetch(`http://${h}:${p}/api/system?token=${encodeURIComponent(t)}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setSystem(await r.json());
    } catch (e) {
      addEvent(`⚠️ Synchronisation système : ${e.message || e}`);
    }
  }

  async function send(c = command) {
    const text = String(c || '').trim();
    if (!text) return;
    if (!token) return Alert.alert('J.A.R.V.I.S.', 'Aucun appareil autorisé.');
    try {
      const r = await fetch(`http://${host}:${port}/api/command`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({token, command: text, confirmed: false})
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`);
      addEvent(`▶ ${text}`);
      addEvent(`↳ ${JSON.stringify(data.result ?? data)}`);
      setCommand('');
    } catch (e) {
      Alert.alert('Commande impossible', String(e.message || e));
    }
  }

  function disconnect() {
    closeWS(); setToken(''); setDeviceId(''); setStatus('Déconnecté'); setScreen('connect');
  }

  if (screen === 'connect') return (
    <SafeAreaView style={s.root}>
      <View style={s.header}><Text style={s.logo}>◈ J.A.R.V.I.S.</Text><Text style={s.sub}>NEO MOBILE</Text></View>
      <ScrollView contentContainerStyle={s.pad}>
        <Text style={s.title}>Connexion au PC</Text>
        <Text style={s.label}>Adresse IP / nom du PC</Text>
        <TextInput value={host} onChangeText={setHost} placeholder="192.168.1.20" placeholderTextColor="#557080" style={s.input} autoCapitalize="none" />
        <Text style={s.label}>Port</Text>
        <TextInput value={port} onChangeText={setPort} keyboardType="number-pad" style={s.input} />
        <Text style={s.label}>Nom de l'appareil</Text>
        <TextInput value={name} onChangeText={setName} style={s.input} />
        <Text style={s.label}>Code d'appairage</Text>
        <TextInput value={code} onChangeText={setCode} keyboardType="number-pad" maxLength={6} style={[s.input, s.code]} />
        <Pressable style={s.button} onPress={pair}><Text style={s.bt}>🔐 APPARIER</Text></Pressable>
        <Text style={s.help}>Le PC doit afficher/générer le code d'appairage. Le token est conservé uniquement sur ce téléphone.</Text>
      </ScrollView>
    </SafeAreaView>
  );

  return (
    <SafeAreaView style={s.root}>
      <View style={s.header}>
        <View><Text style={s.logo}>◈ J.A.R.V.I.S.</Text><Text style={s.sub}>NEO MOBILE</Text></View>
        <Text style={[s.status, status === 'Connecté' ? s.good : s.warn]}>{status}</Text>
      </View>
      <View style={s.tabs}>
        <Tab label="Dashboard" active={tab === 'dashboard'} onPress={() => setTab('dashboard')} />
        <Tab label="Contrôle" active={tab === 'control'} onPress={() => setTab('control')} />
        <Tab label="Événements" active={tab === 'events'} onPress={() => setTab('events')} />
      </View>
      <ScrollView contentContainerStyle={s.pad}>
        {tab === 'dashboard' && <>
          <Text style={s.title}>État du système</Text>
          <View style={s.grid}>
            <Card t="CPU" v={`${system.cpu ?? system.cpu_percent ?? '—'}%`} />
            <Card t="RAM" v={`${system.ram ?? system.ram_percent ?? '—'}%`} />
            <Card t="DISQUE" v={`${system.disk ?? system.disk_percent ?? '—'}%`} />
            <Card t="BATTERIE" v={system.battery == null && system.battery_percent == null ? '—' : `${system.battery ?? system.battery_percent}%`} />
          </View>
          <View style={s.info}><Text style={s.infoText}>IA : {system.provider || '—'} · {system.model || '—'}</Text><Text style={s.infoText}>Micro : {system.mic_enabled ? 'ON' : 'OFF'} · Voix : {system.voice_enabled ? 'ON' : 'OFF'}</Text><Text style={s.infoText}>Écoute : {system.listening ? 'active' : 'repos'} · Traitement : {system.processing ? 'actif' : 'repos'}</Text></View>
        </>}
        {tab === 'control' && <>
          <Text style={s.title}>Contrôle J.A.R.V.I.S.</Text>
          <TextInput value={command} onChangeText={setCommand} placeholder="Commande à J.A.R.V.I.S..." placeholderTextColor="#557080" style={[s.input, s.multi]} multiline />
          <Pressable style={s.button} onPress={() => send()}><Text style={s.bt}>▶ ENVOYER</Text></Pressable>
          <View style={s.row}><Pressable style={s.small} onPress={() => send('ouvre le bloc-notes')}><Text style={s.bt}>📝 Bloc-notes</Text></Pressable><Pressable style={s.small} onPress={() => send('ouvre les téléchargements')}><Text style={s.bt}>📁 Téléchargements</Text></Pressable></View>
        </>}
        {tab === 'events' && <>
          <Text style={s.title}>Centre d'événements</Text>
          {events.length === 0 ? <Text style={s.help}>Aucun événement pour le moment.</Text> : events.map((x, i) => <View key={`${i}-${x}`} style={s.log}><Text style={s.logt}>{x}</Text></View>)}
        </>}
        <Pressable style={s.danger} onPress={disconnect}><Text style={s.bt}>Déconnecter cet appareil</Text></Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

function Tab({label, active, onPress}) { return <Pressable style={[s.tab, active && s.tabActive]} onPress={onPress}><Text style={[s.tabText, active && s.tabTextActive]}>{label}</Text></Pressable>; }
function Card({t, v}) { return <View style={s.card}><Text style={s.label}>{t}</Text><Text style={s.value}>{v}</Text></View>; }

const s = StyleSheet.create({
  root:{flex:1,backgroundColor:'#020617'}, header:{padding:20,borderBottomWidth:1,borderBottomColor:'#12354a',flexDirection:'row',justifyContent:'space-between',alignItems:'center'},
  logo:{color:'#dffcff',fontSize:20,fontWeight:'800'}, sub:{color:'#00dffc',fontSize:11,letterSpacing:3}, status:{fontWeight:'700'}, good:{color:'#00ffaa'}, warn:{color:'#ffcc66'},
  tabs:{flexDirection:'row',borderBottomWidth:1,borderBottomColor:'#12354a',paddingHorizontal:12}, tab:{flex:1,paddingVertical:13,alignItems:'center'}, tabActive:{borderBottomWidth:2,borderBottomColor:'#00dffc'}, tabText:{color:'#668897',fontWeight:'700'}, tabTextActive:{color:'#00dffc'},
  pad:{padding:18,paddingBottom:50}, title:{color:'#dffcff',fontSize:22,fontWeight:'800',marginTop:16,marginBottom:12}, label:{color:'#7fa6b5',fontSize:12,marginBottom:6},
  input:{backgroundColor:'#050d1f',borderWidth:1,borderColor:'#16445b',borderRadius:9,color:'#dffcff',padding:13,marginBottom:14}, code:{fontSize:25,letterSpacing:7,textAlign:'center'}, multi:{minHeight:100,textAlignVertical:'top'},
  button:{backgroundColor:'#08718c',borderRadius:9,padding:15,alignItems:'center',marginVertical:8}, bt:{color:'#e8ffff',fontWeight:'800'}, help:{color:'#668897',marginTop:12,lineHeight:20},
  grid:{flexDirection:'row',flexWrap:'wrap'}, card:{backgroundColor:'#050d1f',borderWidth:1,borderColor:'#12354a',borderRadius:10,padding:13,width:'48%',marginRight:'2%',marginBottom:10}, value:{color:'#00f3ff',fontSize:25,fontWeight:'800'},
  info:{backgroundColor:'#071326',borderWidth:1,borderColor:'#12354a',borderRadius:10,padding:14,marginTop:8}, infoText:{color:'#9fc3ce',lineHeight:24}, row:{flexDirection:'row'}, small:{flex:1,backgroundColor:'#071b32',borderWidth:1,borderColor:'#08718c',borderRadius:8,padding:13,alignItems:'center',marginTop:5,marginRight:4},
  log:{backgroundColor:'#050d1f',borderLeftWidth:2,borderLeftColor:'#08718c',padding:9,marginVertical:3}, logt:{color:'#a9c8d2',fontSize:12}, danger:{marginTop:25,borderWidth:1,borderColor:'#8c2745',borderRadius:9,padding:13,alignItems:'center'}
});
