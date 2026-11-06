import {useEffect,useState} from 'react';
import {
 ActivityIndicator,KeyboardAvoidingView,Platform,Pressable,SafeAreaView,
 ScrollView,StatusBar,StyleSheet,Text,TextInput,View
} from 'react-native';
import * as AuthSession from 'expo-auth-session';
import * as WebBrowser from 'expo-web-browser';
import * as Crypto from 'expo-crypto';
import {
 COGNITO_CLIENT_ID,COGNITO_HOST,isConfigured,kyroApi,
 type Project,type Conversation,type Message,type WorkspaceFile,type TeamPost,type Connector
} from './src/client';

WebBrowser.maybeCompleteAuthSession();

type Tab='home'|'chat'|'code'|'team'|'tools';
const navigation:{id:Tab;title:string;icon:string}[]=[
 {id:'home',title:'Home',icon:'◈'},{id:'chat',title:'Chat',icon:'◫'},
 {id:'code',title:'Code',icon:'⌘'},{id:'team',title:'Team',icon:'◎'},
 {id:'tools',title:'Plugins',icon:'◇'}
];
const redirectUri=AuthSession.makeRedirectUri({native:'kyro://auth/callback'});
const discovery={
 authorizationEndpoint:COGNITO_HOST+'/oauth2/authorize',
 tokenEndpoint:COGNITO_HOST+'/oauth2/token'
};

function Tile({title,detail,onPress,selected=false}:{
 title:string;detail?:string;onPress:()=>void;selected?:boolean
}){
 return <Pressable accessibilityRole="button" onPress={onPress} style={[styles.tile,selected&&styles.tileSelected]}>
   <Text style={styles.tileTitle}>{title}</Text>
   {detail?<Text style={styles.muted}>{detail}</Text>:null}
 </Pressable>;
}
function Button({title,onPress,disabled=false,secondary=false}:{
 title:string;onPress:()=>void;disabled?:boolean;secondary?:boolean
}){
 return <Pressable accessibilityRole="button" disabled={disabled} onPress={onPress}
  style={[styles.button,secondary&&styles.secondary,disabled&&styles.disabled]}>
  <Text style={[styles.buttonLabel,secondary&&styles.secondaryLabel]}>{title}</Text>
 </Pressable>;
}

export default function App(){
 const [request,response,promptAsync]=AuthSession.useAuthRequest({
  clientId:COGNITO_CLIENT_ID||'unconfigured-mobile-client',
  redirectUri,responseType:AuthSession.ResponseType.Code,
  scopes:['openid','email','profile'],usePKCE:true
 },discovery);
 // ID token only in memory. /api/v3/me is the authoritative session check.
 const [idToken,setIdToken]=useState<string|null>(null);
 const [account,setAccount]=useState('');
 const [tab,setTab]=useState<Tab>('home');
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const [projects,setProjects]=useState<Project[]>([]);
 const [projectId,setProjectId]=useState<string|null>(null);
 const [conversations,setConversations]=useState<Conversation[]>([]);
 const [conversationId,setConversationId]=useState<string|null>(null);
 const [messages,setMessages]=useState<Message[]>([]);
 const [chatText,setChatText]=useState('');
 const [files,setFiles]=useState<WorkspaceFile[]>([]);
 const [fileContents,setFileContents]=useState('');
 const [filePath,setFilePath]=useState('');
 const [posts,setPosts]=useState<TeamPost[]>([]);
 const [postText,setPostText]=useState('');
 const [connectors,setConnectors]=useState<Connector[]>([]);
 const selectedProject=projects.find(p=>p.id===projectId);

 const run=async(fn:()=>Promise<void>)=>{
  setBusy(true);setError('');
  try{await fn();}
  catch(err){const message=err instanceof Error?err.message:'Request failed.';
   setError(message);
   if(message.includes('Session expired'))signOut();
  }
  finally{setBusy(false);}
 };
 function signOut(){
  setIdToken(null);setAccount('');setProjects([]);setProjectId(null);
  setConversations([]);setMessages([]);setConversationId(null);
  setFiles([]);setFilePath('');setFileContents('');setPosts([]);setConnectors([]);
 }

 useEffect(()=>{
  if(response?.type!=='success')return;
  const code=response.params.code;
  if(!code||!request?.codeVerifier){setError('Missing sign-in verification.');return;}
  let active=true;
  (async()=>{
   setBusy(true);setError('');
   try{
    const tokens=await AuthSession.exchangeCodeAsync({
     clientId:COGNITO_CLIENT_ID,code,redirectUri,
     extraParams:{code_verifier:request.codeVerifier!}
    },discovery);
    if(!tokens.idToken)throw new Error('Cognito did not return an identity token.');
    const me=await kyroApi<{subject:string}>(tokens.idToken,'/me');
    if(active){setAccount(me.subject||'Member');setIdToken(tokens.idToken);}
   }catch(err){
    if(active)setError(err instanceof Error?err.message:'Sign-in failed.');
   }finally{if(active)setBusy(false);}
  })();
  return()=>{active=false;};
 },[response,request]);

 useEffect(()=>{
  if(!idToken)return;
  let active=true;
  kyroApi<{projects:Project[]}>(idToken,'/projects')
   .then(data=>{if(active){setProjects(data.projects||[]);setProjectId(current=>
    (data.projects||[]).some(p=>p.id===current)?current:(data.projects||[])[0]?.id||null);}})
   .catch(err=>{if(active)setError(err.message);});
  return()=>{active=false;};
 },[idToken]);

 useEffect(()=>{
  if(!idToken)return;
  let active=true;
  const load=async()=>{
   if(tab==='chat'){
    const data=await kyroApi<{conversations:Conversation[]}>(idToken,'/conversations');
    if(active)setConversations(data.conversations||[]);
   }else if(tab==='code'&&projectId){
    const data=await kyroApi<{files:WorkspaceFile[]}>(idToken,'/projects/'+projectId+'/files');
    if(active)setFiles(data.files||[]);
   }else if(tab==='team'&&projectId){
    const data=await kyroApi<{posts:TeamPost[]}>(idToken,'/projects/'+projectId+'/posts');
    if(active)setPosts(data.posts||[]);
   }else if(tab==='tools'){
    const data=await kyroApi<{connectors:Connector[]}>(idToken,'/connectors');
    if(active)setConnectors(data.connectors||[]);
   }
  };
  load().catch(err=>{if(active)setError(err.message);});
  return()=>{active=false;};
 },[idToken,tab,projectId]);

 const openConversation=(id:string)=>run(async()=>{
  if(!idToken)return;
  const data=await kyroApi<{messages:Message[]}>(idToken,'/conversations/'+id+'/messages');
  setConversationId(id);setMessages(data.messages||[]);
 });
 const newConversation=()=>run(async()=>{
  if(!idToken)return;
  const data=await kyroApi<{id:string}>(idToken,'/conversations',{method:'POST',body:{title:'New conversation'}});
  setConversations(current=>[{id:data.id,title:'New conversation'},...current]);
  setConversationId(data.id);setMessages([]);
 });
 const sendChat=()=>run(async()=>{
  const content=chatText.trim();
  if(!idToken||!conversationId||!content)return;
  await kyroApi(idToken,'/conversations/'+conversationId+'/generate',{
   method:'POST',body:{content,request_id:Crypto.randomUUID()}
  });
  setChatText('');
  const data=await kyroApi<{messages:Message[]}>(idToken,'/conversations/'+conversationId+'/messages');
  setMessages(data.messages||[]);
 });
 const openFile=(path:string)=>run(async()=>{
  if(!idToken||!projectId)return;
  const data=await kyroApi<{content:string}>(idToken,'/projects/'+projectId+'/file?path='+encodeURIComponent(path));
  setFilePath(path);setFileContents(data.content||'');
 });
 const sendPost=()=>run(async()=>{
  const body=postText.trim();
  if(!idToken||!projectId||!body)return;
  await kyroApi(idToken,'/projects/'+projectId+'/posts',{method:'POST',body:{body}});
  setPostText('');
  const data=await kyroApi<{posts:TeamPost[]}>(idToken,'/projects/'+projectId+'/posts');
  setPosts(data.posts||[]);
 });
 return <SafeAreaView style={styles.safe}>
  <StatusBar barStyle="dark-content"/>
  <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS==='ios'?'padding':undefined}>
   <View style={styles.header}>
    <View style={styles.brand}><Text style={styles.monogram}>K·</Text>
     <View><Text style={styles.brandName}>KYRO</Text><Text style={styles.strap}>INTELLIGENCE WORKSPACE</Text></View>
    </View>
    {idToken?<Pressable accessibilityRole="button" onPress={signOut}><Text style={styles.signout}>Sign out</Text></Pressable>:null}
   </View>
   {!idToken?
    <ScrollView contentContainerStyle={styles.loggedOut}>
     <Text style={styles.eyebrow}>INTERFACE + MODEL · POWERED BY ENGINE</Text>
     <Text style={styles.hero}>Build what’s next.</Text>
     <Text style={styles.lede}>Your private Kyro workspace for projects, collaboration and experimental Genesis conversations.</Text>
     <View style={styles.card}>
      <Text style={styles.cardTitle}>Secure mobile access</Text>
      <Text style={styles.muted}>Administrator-created accounts only. Sign-in uses Cognito authorization code + PKCE.</Text>
      <Button title={busy?'Signing in…':'Continue with secure sign-in'}
       disabled={!request||!isConfigured||busy} onPress={()=>{setError('');void promptAsync();}}/>
      {!isConfigured?<Text style={styles.warning}>A mobile Cognito app client and registered callback are required before sign-in can be used.</Text>:null}
     </View>
     <Text style={styles.disclosure}>Genesis is a research reference. Protected Aurora execution is not enabled by this app.</Text>
    </ScrollView>:
    <>
     <View style={styles.welcome}><Text style={styles.eyebrow}>PRIVATE ALPHA · AWS SYDNEY</Text><Text style={styles.greeting}>Welcome to Kyro</Text>
      <Text numberOfLines={1} style={styles.muted}>Account {account}</Text></View>
     <ScrollView style={styles.flex} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      {tab==='home'?<>
       <Text style={styles.sectionHeading}>Your projects</Text>
       {projects.length?projects.map(p=><Tile key={p.id} title={p.name} detail={'Role: '+p.role}
        selected={p.id===projectId} onPress={()=>setProjectId(p.id)}/>):<Text style={styles.muted}>No projects available. Create your first project from Kyro web.</Text>}
       <Text style={styles.sectionHeading}>Get started</Text>
       <Tile title="Genesis conversations" detail="Experimental research chat" onPress={()=>setTab('chat')}/>
       <Tile title="Code workspace" detail="Browse authorised project files" onPress={()=>setTab('code')}/>
       <Tile title="Collaboration" detail="Project discussion and messages" onPress={()=>setTab('team')}/>
       <View style={styles.info}><Text style={styles.muted}>Aurora execution is controlled separately and is not accessible from this mobile preview.</Text></View>
      </>:null}
      {tab==='chat'?<>
       <Text style={styles.sectionHeading}>Conversations</Text>
       <Button title="+ New conversation" onPress={newConversation} disabled={busy}/>
       {conversations.map(c=><Tile key={c.id} title={c.title} selected={c.id===conversationId} onPress={()=>openConversation(c.id)}/>)}
       {conversationId?<><Text style={styles.sectionHeading}>Genesis · Research</Text>
        <View style={styles.card}>{messages.map((m,i)=><View key={i} style={styles.message}>
         <Text style={styles.eyebrow}>{m.role}</Text><Text style={styles.body}>{m.content}</Text>
        </View>)}</View>
        <TextInput accessibilityLabel="Message Genesis" placeholder="Ask Genesis…" multiline maxLength={3000}
         value={chatText} onChangeText={setChatText} style={styles.input}/>
        <Button title="Send message" disabled={busy||!chatText.trim()} onPress={sendChat}/>
       </>:<Text style={styles.muted}>Choose a conversation or start one.</Text>}
      </>:null}
      {tab==='code'?<>
       <Text style={styles.sectionHeading}>Project files · Read only</Text>
       <Text style={styles.muted}>{selectedProject?.name||'Choose a project from Home.'}</Text>
       {files.map(f=><Tile key={f.path} title={f.path} selected={f.path===filePath} onPress={()=>openFile(f.path)}/>)}
       {filePath?<View style={styles.codeCard}><Text style={styles.eyebrow}>{filePath}</Text><Text selectable style={styles.codeText}>{fileContents}</Text></View>:null}
       <Text style={styles.disclosure}>File editing and guarded execution remain available only through separately reviewed workflows.</Text>
      </>:null}
      {tab==='team'?<>
       <Text style={styles.sectionHeading}>Project collaboration</Text>
       <Text style={styles.muted}>{selectedProject?.name||'Choose a project from Home.'}</Text>
       {posts.map((p,i)=><View key={i} style={styles.card}>
        <Text style={styles.eyebrow}>{p.author}</Text>
        <Text style={styles.body}>{p.body}</Text>
        <Text style={styles.small}>{p.created_at}</Text>
       </View>)}
       {projectId?<><TextInput accessibilityLabel="Team message" value={postText} onChangeText={setPostText}
        maxLength={2400} multiline placeholder="Message your team…" style={styles.input}/>
        <Button title="Send to team" disabled={busy||!postText.trim()} onPress={sendPost}/></>:null}
      </>:null}
      {tab==='tools'?<>
       <Text style={styles.sectionHeading}>Integrations</Text>
       {connectors.map(c=><View key={c.id} style={styles.card}><Text style={styles.cardTitle}>{c.id}</Text>
        <Text style={styles.muted}>{c.protocol} · {c.scope}</Text>
        <Text style={styles.eyebrow}>{c.state}</Text></View>)}
       <Text style={styles.disclosure}>No plugin or protected runtime operation is activated by viewing its status.</Text>
      </>:null}
      {busy?<ActivityIndicator accessibilityLabel="Loading workspace" style={styles.spinner} color="#4c7891"/>:null}
      {error?<Text accessibilityRole="alert" style={styles.warning}>{error}</Text>:null}
     </ScrollView>
     <View style={styles.tabs}>{navigation.map(n=><Pressable key={n.id}
      onPress={()=>{setTab(n.id);setError('');}} accessibilityRole="tab" accessibilityState={{selected:tab===n.id}}
      style={[styles.tab,tab===n.id&&styles.tabActive]}>
      <Text style={styles.tabIcon}>{n.icon}</Text><Text numberOfLines={1} style={styles.tabLabel}>{n.title}</Text>
     </Pressable>)}</View>
    </>
   }
   {!idToken&&error?<Text accessibilityRole="alert" style={styles.warning}>{error}</Text>:null}
  </KeyboardAvoidingView>
 </SafeAreaView>;
}

const styles=StyleSheet.create({
 flex:{flex:1},safe:{flex:1,backgroundColor:'#f2f5f7'},
 header:{paddingHorizontal:18,paddingTop:12,paddingBottom:11,backgroundColor:'#fff',borderBottomWidth:1,borderBottomColor:'#d9e4eb',flexDirection:'row',justifyContent:'space-between',alignItems:'center'},
 brand:{flexDirection:'row',alignItems:'center',gap:10},monogram:{fontSize:26,fontWeight:'800',color:'#355e77',backgroundColor:'#edf4f8',overflow:'hidden',borderRadius:12,paddingHorizontal:12,paddingVertical:7},
 brandName:{fontSize:18,fontWeight:'800',letterSpacing:3,color:'#263f51'},strap:{fontSize:8,fontWeight:'700',letterSpacing:1.4,color:'#7290a1'},
 signout:{fontWeight:'700',color:'#47718a',padding:8},
 loggedOut:{padding:24,paddingTop:64,gap:18},
 eyebrow:{fontSize:11,letterSpacing:1.5,fontWeight:'700',color:'#4b7891',textTransform:'uppercase'},
 hero:{fontSize:40,fontWeight:'700',letterSpacing:-2,color:'#233e52'},lede:{fontSize:16,lineHeight:25,color:'#5a7182'},
 card:{padding:18,marginBottom:12,backgroundColor:'#fff',borderColor:'#d8e5ec',borderWidth:1,borderRadius:16,gap:10},
 cardTitle:{fontWeight:'700',fontSize:18,color:'#284b63'},
 button:{backgroundColor:'#446c84',padding:15,borderRadius:12,alignItems:'center',marginTop:8,minHeight:48},
 buttonLabel:{color:'#fff',fontWeight:'700',fontSize:14},
 secondary:{backgroundColor:'#e5eef3',borderWidth:1,borderColor:'#c8dbe6'},
 secondaryLabel:{color:'#30556d'},disabled:{opacity:.45},warning:{color:'#9c4232',padding:12,lineHeight:21},
 muted:{color:'#688092',fontSize:13,lineHeight:20},disclosure:{marginTop:12,color:'#657b8d',fontSize:12,lineHeight:19},
 welcome:{padding:16,paddingHorizontal:20,gap:3},greeting:{fontSize:25,fontWeight:'700',color:'#284961'},
 content:{paddingHorizontal:14,paddingBottom:30,gap:10},sectionHeading:{fontWeight:'700',fontSize:18,color:'#284961',marginTop:12,marginBottom:4},
 tile:{backgroundColor:'#fff',borderRadius:13,borderWidth:1,borderColor:'#d8e5ec',padding:15,minHeight:56,justifyContent:'center',gap:4},
 tileSelected:{borderColor:'#547b91',backgroundColor:'#eaf3f8'},
 tileTitle:{color:'#2d526c',fontWeight:'700',fontSize:15},
 body:{fontSize:14,lineHeight:22,color:'#314f64'},message:{paddingVertical:10,borderBottomWidth:1,borderBottomColor:'#e7eef2',gap:6},
 small:{color:'#71899a',fontSize:11},input:{backgroundColor:'#fff',borderWidth:1,borderColor:'#c6d9e4',borderRadius:13,minHeight:64,padding:14,fontSize:16,textAlignVertical:'top',color:'#284961'},
 codeCard:{padding:14,borderRadius:12,backgroundColor:'#fdfefe',borderWidth:1,borderColor:'#dce7ed',gap:9},
 codeText:{fontFamily:Platform.OS==='ios'?'Menlo':'monospace',fontSize:12,color:'#28455b',lineHeight:19},
 info:{padding:18,borderRadius:14,backgroundColor:'#e9f0f5'},spinner:{padding:18},
 tabs:{flexDirection:'row',backgroundColor:'#fff',borderTopWidth:1,borderTopColor:'#d6e2e9',paddingBottom:Platform.OS==='ios'?6:9,paddingHorizontal:4},
 tab:{flex:1,minHeight:58,alignItems:'center',justifyContent:'center',gap:2,paddingHorizontal:2,borderRadius:12},
 tabActive:{backgroundColor:'#e8f2f7'},tabIcon:{fontSize:20,color:'#4b7089'},tabLabel:{fontSize:10,color:'#365971',fontWeight:'700'}
});
