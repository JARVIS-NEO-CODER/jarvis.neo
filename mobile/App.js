import React, {useEffect, useRef, useState} from 'react';
import {SafeAreaView, View, Text, TextInput, Pressable, ScrollView, StyleSheet, Alert} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const DEFAULT_PORT='8890';
const key='jarvis_neo_devices';

export default function App(){
  const [screen,setScreen]=useState('connect');
  const [host,setHost]=useState(''); const [port,setPort]=useState(DEFAULT_PORT);
  const [code,setCode]=useState(''); const [name,setName]=useState('Mon téléphone');
  const [token,setToken]=useState(''); const [deviceId,setDeviceId]=useState('');
  const [status,setStatus]=useState('Déconnecté'); const [system,setSystem]=useState({});
  const [command,setCommand]=useState(''); const [log,setLog]=useState([]); const ws=useRef(null);

  useEffect(()=>{load(); return ()=>closeWS()},[]);
  async function load(){
    const raw=await AsyncStorage.getItem(key); const devices=raw?JSON.parse(raw):[];
    if(devices.length){const d=devices[0];setHost(d.host);setPort(d.port);setToken(d.token);setDeviceId(d.deviceId);setScreen('home');connect(d.host,d.port,d.token)}
  }
  async function save(d){const raw=await AsyncStorage.getItem(key);const a=raw?JSON.parse(raw):[];const rest=a.filter(x=>x.deviceId!==d.deviceId);await AsyncStorage.setItem(key,JSON.stringify([d,...rest]))}
  async function pair(){
    if(!host||!code)return Alert.alert('Connexion','Entre l’adresse IP du PC et le code.');
    try{const r=await fetch(`http://${host}:${port}/api/pair`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code,name})});if(!r.ok)throw new Error(await r.text());const d=await r.json();setToken(d.token);setDeviceId(d.device_id);await save({host,port,token:d.token,deviceId:d.device_id,name});setScreen('home');connect(host,port,d.token)}catch(e){Alert.alert('Appairage impossible',String(e.message||e))}
  }
  function closeWS(){if(ws.current){ws.current.close();ws.current=null}}
  function connect(h,p,t){
    closeWS();setStatus('Connexion…');
    const proto=h==='localhost'||h==='127.0.0.1'?'ws':'ws'; const s=new WebSocket(`${proto}://${h}:${p}/ws?token=${encodeURIComponent(t)}`);ws.current=s;
    s.onopen=()=>{setStatus('Connecté');add('🟢 J.A.R.V.I.S. connecté');fetchSystem(h,p)};
    s.onclose=()=>setStatus('Déconnecté');s.onerror=()=>setStatus('Erreur réseau');
    s.onmessage=e=>{try{const m=JSON.parse(e.data);add(JSON.stringify(m));}catch{add(e.data)}}
  }
  function add(x){setLog(l=>[String(x),...l].slice(0,40))}
  async function fetchSystem(h=host,p=port){try{const r=await fetch(`http://${h}:${p}/api/system`);setSystem(await r.json())}catch{} }
  async function send(c,confirmed=false){
    if(!token)return Alert.alert('J.A.R.V.I.S.','Aucun appareil autorisé.');
    try{const r=await fetch(`http://${host}:${port}/api/command`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,command:c,confirmed})});const x=await r.json();add(JSON.stringify(x));if(x.confirmation_required)Alert.alert('Confirmation requise','Cette action est sensible.');}catch(e){Alert.alert('Erreur',String(e.message||e))}
  }
  function disconnect(){closeWS();setToken('');setDeviceId('');setStatus('Déconnecté');setScreen('connect')}
  if(screen==='connect')return <SafeAreaView style={s.root}><View style={s.header}><Text style={s.logo}>◈ J.A.R.V.I.S.</Text><Text style={s.sub}>NEO MOBILE</Text></View><ScrollView contentContainerStyle={s.pad}><Text style={s.title}>Connexion au PC</Text><Text style={s.label}>Adresse IP / nom du PC</Text><TextInput value={host} onChangeText={setHost} placeholder="192.168.1.20" placeholderTextColor="#557080" style={s.input} autoCapitalize="none"/><Text style={s.label}>Port</Text><TextInput value={port} onChangeText={setPort} keyboardType="number-pad" style={s.input}/><Text style={s.label}>Nom de l’appareil</Text><TextInput value={name} onChangeText={setName} style={s.input}/><Text style={s.label}>Code d’appairage</Text><TextInput value={code} onChangeText={setCode} keyboardType="number-pad" maxLength={6} style={[s.input,s.code]}/><Pressable style={s.button} onPress={pair}><Text style={s.bt}>🔐 APPARIER</Text></Pressable><Text style={s.help}>Sur le PC : J.A.R.V.I.S. NEO → Appareils → Générer un code.</Text></ScrollView></SafeAreaView>;
  return <SafeAreaView style={s.root}><View style={s.header}><View><Text style={s.logo}>◈ J.A.R.V.I.S.</Text><Text style={s.sub}>NEO MOBILE</Text></View><Text style={[s.status,status==='Connecté'?s.good:s.warn]}>{status}</Text></View><ScrollView contentContainerStyle={s.pad}><View style={s.grid}><Card t="CPU" v={(system.cpu??'—')+'%'}/><Card t="RAM" v={(system.ram??'—')+'%'}/><Card t="DISQUE" v={(system.disk??'—')+'%'}/><Card t="BATTERIE" v={system.battery==null?'—':system.battery+'%'}/></View><Text style={s.title}>Contrôle</Text><TextInput value={command} onChangeText={setCommand} placeholder="Commande à J.A.R.V.I.S..." placeholderTextColor="#557080" style={[s.input,s.multi]}/><Pressable style={s.button} onPress={()=>send(command)}><Text style={s.bt}>▶ ENVOYER</Text></Pressable><View style={s.row}><Pressable style={s.small} onPress={()=>send('ouvre le bloc-notes')}><Text style={s.bt}>📝 Bloc-notes</Text></Pressable><Pressable style={s.small} onPress={()=>send('ouvre les téléchargements')}><Text style={s.bt}>📁 Téléchargements</Text></Pressable></View><Text style={s.title}>Événements</Text>{log.map((x,i)=><View key={i} style={s.log}><Text style={s.logt}>{x}</Text></View>)}<Pressable style={s.danger} onPress={disconnect}><Text style={s.bt}>Déconnecter cet appareil</Text></Pressable></ScrollView></SafeAreaView>
}
function Card({t,v}){return <View style={s.card}><Text style={s.label}>{t}</Text><Text style={s.value}>{v}</Text></View>}
const s=StyleSheet.create({root:{flex:1,backgroundColor:'#020617'},header:{padding:20,borderBottomWidth:1,borderBottomColor:'#12354a',flexDirection:'row',justifyContent:'space-between',alignItems:'center'},logo:{color:'#dffcff',fontSize:20,fontWeight:'800'},sub:{color:'#00dffc',fontSize:11,letterSpacing:3},status:{fontWeight:'700'},good:{color:'#00ffaa'},warn:{color:'#ffcc66'},pad:{padding:18,paddingBottom:50},title:{color:'#dffcff',fontSize:22,fontWeight:'800',marginTop:16,marginBottom:12},label:{color:'#7fa6b5',fontSize:12,marginBottom:6},input:{backgroundColor:'#050d1f',borderWidth:1,borderColor:'#16445b',borderRadius:9,color:'#dffcff',padding:13,marginBottom:14},code:{fontSize:25,letterSpacing:7,textAlign:'center'},multi:{minHeight:80,textAlignVertical:'top'},button:{backgroundColor:'#08718c',borderRadius:9,padding:15,alignItems:'center',marginVertical:8},bt:{color:'#e8ffff',fontWeight:'800'},help:{color:'#668897',marginTop:12,lineHeight:20},grid:{flexDirection:'row',flexWrap:'wrap',gap:10},card:{backgroundColor:'#050d1f',borderWidth:1,borderColor:'#12354a',borderRadius:10,padding:13,width:'47%'},value:{color:'#00f3ff',fontSize:25,fontWeight:'800'},row:{flexDirection:'row',gap:8},small:{flex:1,backgroundColor:'#071b32',borderWidth:1,borderColor:'#08718c',borderRadius:8,padding:13,alignItems:'center',marginTop:5},log:{backgroundColor:'#050d1f',borderLeftWidth:2,borderLeftColor:'#08718c',padding:9,marginVertical:3},logt:{color:'#a9c8d2',fontSize:12},danger:{marginTop:25,borderWidth:1,borderColor:'#8c2745',borderRadius:9,padding:13,alignItems:'center'}});
