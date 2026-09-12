import React, {useEffect, useRef, useState} from 'react';
import {SafeAreaView, View, Text, TextInput, Pressable, ScrollView, StyleSheet, Alert} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const DEFAULT_PORT = '8890';
const STORAGE_KEY = 'jarvis_neo_devices';
const PROTOCOL = 'jarvis-neo/1';

export default function App() {
  const [screen, setScreen] = useState('connect');
  const [tab, setTab] = useState('dashboard');
  const [mode, setMode] = useState('local');
  const [host, setHost] = useState('');
  const [port, setPort] = useState(DEFAULT_PORT);
  const [relayUrl, setRelayUrl] = useState('');
  const [remoteNodeId, setRemoteNodeId] = useState('');
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
  const connectionRef = useRef({mode:'local'});

  useEffect(() => { load(); return () => closeWS(); }, []);

  async function load() {
    try {
      const raw = await AsyncStorage.getItem(STORAGE_KEY);
      const devices = raw ? JSON.parse(raw) : [];
      if (devices.length) {
        const d = devices[0];
        setHost(d.host || ''); setPort(d.port || DEFAULT_PORT); setRelayUrl(d.relayUrl || '');
        setRemoteNodeId(d.remoteNodeId || ''); setToken(d.token || ''); setDeviceId(d.deviceId || ''); setName(d.name || 'Mon téléphone');
        if (d.token && d.deviceId) { setMode(d.mode || 'local'); setScreen('home'); setTimeout(() => connect(d), 0); }
      }
    } catch (e) { addEvent(`Impossible de charger les appareils : ${e.message || e}`); }
  }

  async function save(device) {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    const devices = raw ? JSON.parse(raw) : [];
    const rest = devices.filter(x => x.deviceId !== device.deviceId);
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify([device, ...rest]));
  }

  async function pair() {
    if (!host.trim() || !code.trim()) return Alert.alert('Appairage', "Entre l'adresse IP du PC et le code d'appairage.");
    try {
      const r = await fetch(`http://${host.trim()}:${port}/api/pair`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({protocol:PROTOCOL,code:code.trim(),name:name.trim(),device_id:deviceId || undefined})});
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || 'Appairage refusé');
      const device = {host:host.trim(),port,relayUrl:relayUrl.trim(),remoteNodeId,token:data.token,deviceId:data.device_id,name:name.trim(),mode:'local'};
      setToken(data.token); setDeviceId(data.device_id); setScreen('home'); setTab('dashboard'); setMode('local');
      await save(device); connect(device);
    } catch (e) { Alert.alert('Appairage impossible', String(e.message || e)); }
  }

  function closeWS() {
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    if (pingTimer.current) clearInterval(pingTimer.current);
    reconnectTimer.current = null; pingTimer.current = null;
    if (ws.current) { try { ws.current.close(); } catch {} ws.current = null; }
  }

  function connect(device = {mode,host,port,relayUrl,remoteNodeId,token,deviceId}) {
    const targetMode = device.mode || mode;
    if (!device.token || !device.deviceId) return;
    if (targetMode === 'local' && (!device.host || !device.port)) return;
    if (targetMode === 'remote' && (!device.relayUrl || !device.remoteNodeId)) return;
    closeWS(); connectionRef.current = device; setStatus('Connexion…');
    const url = targetMode === 'remote' ? `${device.relayUrl.replace(/\/$/,'')}/ws` : `ws://${device.host}:${device.port}/ws`;
    const socket = new WebSocket(url); ws.current = socket;
    socket.onopen = () => {
      if (targetMode === 'remote') {
        socket.send(JSON.stringify({type:'remote',protocol:PROTOCOL,node_id:device.remoteNodeId}));
      } else {
        socket.send(JSON.stringify({type:'authenticate',protocol:PROTOCOL,token:device.token,device_id:device.deviceId}));
      }
    };
    socket.onclose = () => {
      setStatus('Déconnecté'); if (pingTimer.current) clearInterval(pingTimer.current);
      if (screen === 'home') reconnectTimer.current = setTimeout(() => connect(connectionRef.current), 2500);
    };
    socket.onerror = () => setStatus('Erreur réseau');
    socket.onmessage = e => {
      try {
        const message = JSON.parse(e.data);
        if (message.type === 'remote_attached') {
          socket.send(JSON.stringify({type:'authenticate',protocol:PROTOCOL,token:device.token,device_id:device.deviceId}));
          return;
        }
        if (message.type === 'authenticated') {
          setStatus('Connecté'); addEvent(`🟢 J.A.R.V.I.S. connecté en ${targetMode === 'remote' ? 'mode distant' : 'mode local'}`);
          socket.send(JSON.stringify({type:'status',protocol:PROTOCOL,token:device.token,device_id:device.deviceId,request_id:`status-${Date.now()}`}));
          pingTimer.current = setInterval(() => {
            if (ws.current?.readyState === 1) ws.current.send(JSON.stringify({type:'ping',protocol:PROTOCOL,token:device.token,device_id:device.deviceId,request_id:`ping-${Date.now()}`}));
          }, 15000);
          return;
        }
        if (message.type === 'state') { setSystem(message.state || {}); return; }
        if (message.type === 'event') { addEvent(message.event ? `${message.event}: ${JSON.stringify(message.payload || {})}` : JSON.stringify(message)); return; }
        if (message.type === 'response') { if (message.result?.pong) return; addEvent(`↳ ${JSON.stringify(message.result ?? message)}`); return; }
        if (message.type === 'error') { addEvent(`⚠️ ${message.code || 'Erreur réseau'}`); if (message.code === 'UNAUTHORIZED') setStatus('Non autorisé'); return; }
        if (message.type !== 'relay_ping') addEvent(JSON.stringify(message));
      } catch { addEvent(e.data); }
    };
  }

  function addEvent(value) { setEvents(list => [String(value), ...list].slice(0,80)); }

  async function fetchSystem() {
    if (mode !== 'local' || !host || !token || !deviceId) return;
    try {
      const r = await fetch(`http://${host}:${port}/api/system?token=${encodeURIComponent(token)}&device_id=${encodeURIComponent(deviceId)}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setSystem(await r.json());
    } catch (e) { addEvent(`⚠️ Synchronisation système : ${e.message || e}`); }
  }

  function send(c = command) {
    const text = String(c || '').trim();
    if (!text) return;
    if (!token || !deviceId) return Alert.alert('J.A.R.V.I.S.', 'Aucun appareil autorisé.');
    if (!ws.current || ws.current.readyState !== 1) return Alert.alert('J.A.R.V.I.S.', 'La connexion n’est pas établie.');
    const request_id = `action-${Date.now()}`;
    ws.current.send(JSON.stringify({type:'action',protocol:PROTOCOL,token,device_id:deviceId,request_id,action:'command',args:{command:text,confirmed:false}}));
    addEvent(`▶ ${text}`); setCommand('');
  }

  async function activateRemote() {
    if (!relayUrl.trim() || !remoteNodeId.trim()) return Alert.alert('Mode distant', 'Renseigne l’URL WSS du relais et le node ID du PC.');
    if (!token || !deviceId) return Alert.alert('Mode distant', 'Apparie d’abord ce téléphone au PC en mode local.');
    const device={host,port,relayUrl:relayUrl.trim(),remoteNodeId:remoteNodeId.trim(),token,deviceId,name,mode:'remote'};
    setMode('remote'); await save(device); connect(device);
  }

  async function activateLocal() {
    if (!host.trim()) return Alert.alert('Mode local', 'Renseigne l’adresse du PC.');
    const device={host:host.trim(),port,relayUrl,remoteNodeId,token,deviceId,name,mode:'local'};
    setMode('local'); await save(device); connect(device);
  }

  function disconnect() { closeWS(); setStatus('Déconnecté'); setScreen('connect'); }

  if (screen === 'connect') return (
    <SafeAreaView style={s.root}>
      <View style={s.header}><Text style={s.logo}>◈ J.A.R.V.I.S.</Text><Text style={s.sub}>NEO MOBILE</Text></View>
      <ScrollView contentContainerStyle={s.pad}>
        <Text style={s.title}>Connexion</Text>
        <View style={s.modeRow}><Pressable style={[s.modeButton,mode==='local'&&s.modeActive]} onPress={()=>setMode('local')}><Text style={s.bt}>LOCAL</Text></Pressable><Pressable style={[s.modeButton,mode==='remote'&&s.modeActive]} onPress={()=>setMode('remote')}><Text style={s.bt}>DISTANT</Text></Pressable></View>
        {mode === 'local' && <>
          <Text style={s.label}>Adresse IP / nom du PC</Text><TextInput value={host} onChangeText={setHost} placeholder="192.168.1.20" placeholderTextColor="#557080" style={s.input} autoCapitalize="none" />
          <Text style={s.label}>Port</Text><TextInput value={port} onChangeText={setPort} keyboardType="number-pad" style={s.input} />
          <Text style={s.label}>Nom de l'appareil</Text><TextInput value={name} onChangeText={setName} style={s.input} />
          <Text style={s.label}>Code d'appairage</Text><TextInput value={code} onChangeText={setCode} keyboardType="number-pad" maxLength={6} style={[s.input,s.code]} />
          <Pressable style={s.button} onPress={pair}><Text style={s.bt}>🔐 APPARIER</Text></Pressable>
          <Text style={s.help}>Le premier appairage se fait sur le réseau local. Ensuite, le même appareil peut utiliser le relais distant.</Text>
        </>}
        {mode === 'remote' && <>
          <Text style={s.label}>URL du relais WSS</Text><TextInput value={relayUrl} onChangeText={setRelayUrl} placeholder="wss://relais.example/ws" placeholderTextColor="#557080" style={s.input} autoCapitalize="none" />
          <Text style={s.label}>Node ID du PC</Text><TextInput value={remoteNodeId} onChangeText={setRemoteNodeId} placeholder="identifiant du PC" placeholderTextColor="#557080" style={s.input} autoCapitalize="none" />
          <Pressable style={s.button} onPress={activateRemote}><Text style={s.bt}>🌐 CONNECTER À DISTANCE</Text></Pressable>
          <Text style={s.help}>Le PC doit avoir un tunnel sortant actif vers le relais. Aucune ouverture de port Internet sur le PC n’est nécessaire.</Text>
        </>}
      </ScrollView>
    </SafeAreaView>
  );

  return (
    <SafeAreaView style={s.root}>
      <View style={s.header}><View><Text style={s.logo}>◈ J.A.R.V.I.S.</Text><Text style={s.sub}>NEO MOBILE · {mode.toUpperCase()}</Text></View><Text style={[s.status,status==='Connecté'?s.good:s.warn]}>{status}</Text></View>
      <View style={s.tabs}><Tab label="Dashboard" active={tab==='dashboard'} onPress={()=>setTab('dashboard')} /><Tab label="Contrôle" active={tab==='control'} onPress={()=>setTab('control')} /><Tab label="Événements" active={tab==='events'} onPress={()=>setTab('events')} /></View>
      <ScrollView contentContainerStyle={s.pad}>
        {tab==='dashboard' && <><Text style={s.title}>État du système</Text><View style={s.grid}><Card t="CPU" v={`${system.cpu_percent ?? '—'}%`} /><Card t="RAM" v={`${system.ram_percent ?? '—'}%`} /><Card t="DISQUE" v={`${system.disk_percent ?? '—'}%`} /><Card t="BATTERIE" v={system.battery_percent == null?'—':`${system.battery_percent}%`} /></View><View style={s.info}><Text style={s.infoText}>IA : {system.provider||'—'} · {system.model||'—'}</Text><Text style={s.infoText}>Micro : {system.mic_enabled?'ON':'OFF'} · Voix : {system.voice_enabled?'ON':'OFF'}</Text><Text style={s.infoText}>Écoute : {system.listening?'active':'repos'} · Traitement : {system.processing?'actif':'repos'}</Text>{system.remote_node_id&&<Text style={s.infoText}>Node distant : {system.remote_node_id}</Text>}</View></>}
        {tab==='control' && <><Text style={s.title}>Contrôle J.A.R.V.I.S.</Text><TextInput value={command} onChangeText={setCommand} placeholder="Commande à J.A.R.V.I.S..." placeholderTextColor="#557080" style={[s.input,s.multi]} multiline /><Pressable style={s.button} onPress={()=>send()}><Text style={s.bt}>▶ ENVOYER</Text></Pressable><View style={s.row}><Pressable style={s.small} onPress={()=>send('ouvre le bloc-notes')}><Text style={s.bt}>📝 Bloc-notes</Text></Pressable><Pressable style={s.small} onPress={()=>send('ouvre les téléchargements')}><Text style={s.bt}>📁 Téléchargements</Text></Pressable></View></>}
        {tab==='events' && <><Text style={s.title}>Centre d'événements</Text>{events.length===0?<Text style={s.help}>Aucun événement pour le moment.</Text>:events.map((x,i)=><View key={`${i}-${x}`} style={s.log}><Text style={s.logt}>{x}</Text></View>)}</>}
        <View style={s.row}><Pressable style={s.small} onPress={activateLocal}><Text style={s.bt}>↔ LOCAL</Text></Pressable><Pressable style={s.small} onPress={activateRemote}><Text style={s.bt}>🌐 DISTANT</Text></Pressable></View>
        <Pressable style={s.danger} onPress={disconnect}><Text style={s.bt}>Déconnecter cet appareil</Text></Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

function Tab({label,active,onPress}){return <Pressable style={[s.tab,active&&s.tabActive]} onPress={onPress}><Text style={[s.tabText,active&&s.tabTextActive]}>{label}</Text></Pressable>}
function Card({t,v}){return <View style={s.card}><Text style={s.label}>{t}</Text><Text style={s.value}>{v}</Text></View>}
const s=StyleSheet.create({
 root:{flex:1,backgroundColor:'#020617'},header:{padding:20,borderBottomWidth:1,borderBottomColor:'#12354a',flexDirection:'row',justifyContent:'space-between',alignItems:'center'},logo:{color:'#dffcff',fontSize:20,fontWeight:'800'},sub:{color:'#00dffc',fontSize:11,letterSpacing:3},status:{fontWeight:'700'},good:{color:'#00ffaa'},warn:{color:'#ffcc66'},
 tabs:{flexDirection:'row',borderBottomWidth:1,borderBottomColor:'#12354a',paddingHorizontal:12},tab:{flex:1,paddingVertical:13,alignItems:'center'},tabActive:{borderBottomWidth:2,borderBottomColor:'#00dffc'},tabText:{color:'#668897',fontWeight:'700'},tabTextActive:{color:'#00dffc'},
 pad:{padding:18,paddingBottom:50},title:{color:'#dffcff',fontSize:22,fontWeight:'800',marginTop:16,marginBottom:12},label:{color:'#7fa6b5',fontSize:12,marginBottom:6},input:{backgroundColor:'#050d1f',borderWidth:1,borderColor:'#16445b',borderRadius:9,color:'#dffcff',padding:13,marginBottom:14},code:{fontSize:25,letterSpacing:7,textAlign:'center'},multi:{minHeight:100,textAlignVertical:'top'},
 modeRow:{flexDirection:'row',marginBottom:10},modeButton:{flex:1,backgroundColor:'#071b32',borderWidth:1,borderColor:'#16445b',borderRadius:8,padding:12,alignItems:'center',marginRight:4},modeActive:{borderColor:'#00dffc',backgroundColor:'#08718c'},button:{backgroundColor:'#08718c',borderRadius:9,padding:15,alignItems:'center',marginVertical:8},bt:{color:'#e8ffff',fontWeight:'800'},help:{color:'#668897',marginTop:12,lineHeight:20},
 grid:{flexDirection:'row',flexWrap:'wrap'},card:{backgroundColor:'#050d1f',borderWidth:1,borderColor:'#12354a',borderRadius:10,padding:13,width:'48%',marginRight:'2%',marginBottom:10},value:{color:'#00f3ff',fontSize:25,fontWeight:'800'},info:{backgroundColor:'#071326',borderWidth:1,borderColor:'#12354a',borderRadius:10,padding:14,marginTop:8},infoText:{color:'#9fc3ce',lineHeight:24},row:{flexDirection:'row',marginTop:6},small:{flex:1,backgroundColor:'#071b32',borderWidth:1,borderColor:'#08718c',borderRadius:8,padding:13,alignItems:'center',marginRight:4},log:{backgroundColor:'#050d1f',borderLeftWidth:2,borderLeftColor:'#08718c',padding:9,marginVertical:3},logt:{color:'#a9c8d2',fontSize:12},danger:{marginTop:25,borderWidth:1,borderColor:'#8c2745',borderRadius:9,padding:13,alignItems:'center'}
});
