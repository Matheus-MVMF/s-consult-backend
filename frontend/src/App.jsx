import { useState, useRef, useEffect } from 'react';
import { Menu, Loader2, FileText, Copy, Check, LogOut, UploadCloud, FileSpreadsheet } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import logo from './Logo.jpeg'; 
import { auth } from './firebase';
import { signInWithEmailAndPassword, onAuthStateChanged, signOut } from "firebase/auth";

export default function App() {
  const [user, setUser] = useState(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  // Agora o sistema tem apenas os dois módulos de Upload
  const [activeModule, setActiveModule] = useState('inventario');
  const [messages, setMessages] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);
  
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const hasStarted = messages.length > 0;
  
  // ⚠️ Link do Backend
  const API_URL = "https://s-consult-backend.onrender.com";

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => setUser(currentUser));
    return () => unsubscribe();
  }, []);

  const handleLogin = async () => {
    if (!email || !password) return;
    setLoginError('');
    setIsLoggingIn(true);
    try {
      await signInWithEmailAndPassword(auth, email, password);
    } catch {
      setLoginError("Acesso negado. Verifique as credenciais.");
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleLogout = () => signOut(auth);

  const switchModule = (modulo) => {
    setActiveModule(modulo);
    setMessages([]); // Limpa a tela ao trocar de módulo
  };

  // Função ÚNICA e inteligente para Upload
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Decide o nome e a rota (endpoint) baseado no módulo selecionado na lateral
    const isRelatorio = activeModule === 'relatorio';
    const moduleName = isRelatorio ? 'Novo Relatório' : 'Inventário (Tabelas Antigas)';
    const endpoint = isRelatorio ? '/upload-relatorio' : '/upload-inventario';

    setMessages(prev => [...prev, { role: 'user', content: `📄 ${moduleName} Enviado:\n${file.name}` }]);
    setIsLoading(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: "❌ Falha ao conectar com o servidor para envio do PDF." }]);
    } finally {
      setIsLoading(false);
      event.target.value = null; // Reseta o input para permitir enviar o mesmo arquivo de novo
    }
  };

  // Formatação perfeita para o WhatsApp
  const copyToClipboard = (text, index) => {
    const cleanText = text
      .replace(/###\s?/g, '')       
      .replace(/>\s?/g, '')         
      .replace(/\*\*/g, '')         
      .replace(/\*/g, '')           
      .replace(/---/g, '')          
      .replace(/\n\s*\n\s*\n/g, '\n\n') 
      .trim();

    navigator.clipboard.writeText(cleanText).then(() => {
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000); 
    });
  };

  // TELA DE LOGIN
  if (!user) {
    return (
      <div className="min-h-screen bg-[#121212] flex items-center justify-center p-4 font-sans text-gray-100">
        <div className="bg-[#1a1a1a] p-8 rounded-3xl border border-gray-800 w-full max-w-md shadow-2xl">
          <div className="flex justify-center mb-8"><img src={logo} alt="S Consult" className="h-24 object-contain" /></div>
          <h2 className="text-2xl font-bold text-white mb-2 text-center">Portal S Consult</h2>
          <div className="space-y-4 mt-6">
            <input type="email" placeholder="E-mail corporativo" className="w-full p-4 bg-[#0a0a0a] border border-gray-700 rounded-xl text-white outline-none focus:border-yellow-500" onChange={(e) => setEmail(e.target.value)} />
            <input type="password" placeholder="Senha de acesso" className="w-full p-4 bg-[#0a0a0a] border border-gray-700 rounded-xl text-white outline-none focus:border-yellow-500" onChange={(e) => setPassword(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleLogin()} />
            {loginError && <div className="text-red-500 text-xs text-center font-bold">{loginError}</div>}
            <button onClick={handleLogin} disabled={isLoggingIn} className="w-full py-4 bg-yellow-500 text-black font-black rounded-xl hover:bg-yellow-400 active:scale-95 uppercase tracking-widest">
              {isLoggingIn ? <Loader2 className="w-6 h-6 animate-spin mx-auto" /> : "Acessar Sistema"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // TELA PRINCIPAL (LOGADO)
  return (
    <div className="min-h-screen bg-[#121212] flex font-sans text-gray-100 selection:bg-yellow-500/30 overflow-hidden">
      
      {/* MENU LATERAL */}
      <aside className={`${sidebarOpen ? 'w-72' : 'w-0'} bg-[#0a0a0a] border-r border-gray-800 transition-all duration-300 overflow-hidden flex flex-col shrink-0 z-20`}>
        <div className="p-8 border-b border-gray-800 flex justify-center bg-black/20">
          <img src={logo} alt="S Consult" className="h-20 object-contain drop-shadow-2xl" />
        </div>
        
        <div className="flex-1 overflow-y-auto p-4">
          <h3 className="text-[10px] font-bold text-gray-500 uppercase mb-4 tracking-widest pl-2">Módulos de Upload</h3>
          <div className="space-y-3">
            <button onClick={() => switchModule('inventario')} className={`w-full flex items-center gap-4 p-4 rounded-xl transition-all border text-left ${activeModule === 'inventario' ? 'bg-[#1f1f1f] border-yellow-500 text-white' : 'border-transparent text-gray-400 hover:bg-[#1a1a1a]'}`}>
              <div className={`p-2 rounded-lg ${activeModule === 'inventario' ? 'bg-yellow-500/10 text-yellow-500' : 'bg-gray-800'}`}><FileSpreadsheet className="w-5 h-5" /></div>
              <div><div className="text-sm font-bold">Processar Inventário</div><div className="text-[10px] text-gray-500">Formato Tabelas Antigas</div></div>
            </button>
            <button onClick={() => switchModule('relatorio')} className={`w-full flex items-center gap-4 p-4 rounded-xl transition-all border text-left ${activeModule === 'relatorio' ? 'bg-[#1f1f1f] border-yellow-500 text-white' : 'border-transparent text-gray-400 hover:bg-[#1a1a1a]'}`}>
              <div className={`p-2 rounded-lg ${activeModule === 'relatorio' ? 'bg-yellow-500/10 text-yellow-500' : 'bg-gray-800'}`}><UploadCloud className="w-5 h-5" /></div>
              <div><div className="text-sm font-bold">Processar Relatório</div><div className="text-[10px] text-gray-500">Novo Modelo Completo</div></div>
            </button>
          </div>
        </div>

        <div className="p-4 border-t border-gray-800">
           <button onClick={handleLogout} className="w-full flex items-center gap-3 p-3 text-gray-500 hover:text-red-500 rounded-lg transition-all text-sm font-bold uppercase tracking-tighter">
             <LogOut className="w-4 h-4" /> Sair do Sistema
           </button>
        </div>
      </aside>

      {/* ÁREA CENTRAL */}
      <div className="flex-1 flex flex-col h-screen relative bg-[#121212]">
        <header className="h-16 flex items-center px-6 border-b border-gray-800/60 bg-[#0a0a0a] sticky top-0 z-10">
            <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-2 mr-4 bg-[#1f1f1f] rounded-lg text-white hover:bg-gray-700 border border-gray-700"><Menu className="w-5 h-5" /></button>
            <span className="text-xs font-black text-gray-500 uppercase tracking-[0.3em]">
              {activeModule === 'inventario' ? 'MÓDULO: LEITURA DE INVENTÁRIOS (ANTIGO)' : 'MÓDULO: LEITURA DE NOVOS RELATÓRIOS'}
            </span>
        </header>

        <main className={`flex-1 overflow-y-auto px-4 md:px-10 transition-all duration-500 pb-32 pt-10`}>
          {!hasStarted ? (
            <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
                <div className="w-20 h-20 bg-[#1f1f1f] rounded-3xl flex items-center justify-center mb-6 border border-gray-800 shadow-[0_0_50px_rgba(234,179,8,0.1)]">
                    {activeModule === 'inventario' ? <FileSpreadsheet className="w-10 h-10 text-yellow-500" /> : <FileText className="w-10 h-10 text-yellow-500" />}
                </div>
                <h1 className="text-4xl font-bold text-white mb-2">
                  {activeModule === 'inventario' ? 'Processar Inventário' : 'Processar Relatório'}
                </h1>
                <p className="text-gray-400 text-sm max-w-sm">
                  {activeModule === 'inventario' 
                    ? 'Faça o upload das tabelas (formato antigo/Excel) para gerar o resumo técnico.' 
                    : 'Faça o upload do NOVO modelo de relatório para extração e geração de resumo.'}
                </p>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto space-y-8">
              {messages.map((message, index) => (
                <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-in slide-in-from-bottom-4`}>
                  <div className={`w-full ${message.role === 'user' ? 'max-w-md bg-[#2f2f2f] text-white p-4 rounded-2xl rounded-br-none border border-gray-700 whitespace-pre-wrap' : 'max-w-4xl bg-[#1a1a1a] border border-gray-800 rounded-2xl p-6 md:p-8 shadow-2xl relative'}`}>
                    
                    {message.role === 'assistant' && (
                        <>
                          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-yellow-600 via-yellow-400 to-yellow-600"></div>
                          
                          {!message.content.includes("❌") && (
                              <button onClick={() => copyToClipboard(message.content, index)} className="absolute top-4 right-4 p-2 bg-[#252525] hover:bg-yellow-500 hover:text-black rounded-lg transition-colors border border-gray-700 flex items-center gap-2">
                                  {copiedIndex === index ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                                  <span className="text-xs font-bold">{copiedIndex === index ? "Copiado!" : "WhatsApp"}</span>
                              </button>
                          )}
                        </>
                    )}

                    <div className="prose prose-invert max-w-none text-gray-300">
                        {message.content.includes("❌") ? (
                            <span className="text-red-400 font-bold">{message.content}</span>
                        ) : (
                           <ReactMarkdown
                            components={{
                            h3: ({node, ...props}) => <h3 className="text-yellow-500 font-bold text-lg mt-6 mb-3 border-b border-gray-700 pb-2" {...props} />,
                            h4: ({node, ...props}) => <h4 className="text-yellow-400 font-semibold mt-4 mb-2" {...props} />,
                            strong: ({node, ...props}) => <strong className="text-yellow-200 font-bold" {...props} />,
                            ul: ({node, ...props}) => <ul className="space-y-2 my-3 text-gray-300" {...props} />,
                            li: ({node, ...props}) => (
                              <li className="flex items-start gap-2">
                                <span className="text-yellow-500 mt-1">•</span>
                                <span {...props} />
                              </li>
                            ),
                            blockquote: ({node, ...props}) => (
                              <blockquote className="bg-[#2a2a2a] border-l-4 border-yellow-500 p-4 rounded-r-lg my-4 text-gray-200 shadow-md" {...props} />
                            ),
                            hr: ({node, ...props}) => <hr className="my-6 border-gray-700" {...props} />
                          }}
                        >
                          {message.content}
                        </ReactMarkdown>
                        )}
                    </div>
                  </div>
                </div>
              ))}
              
              {isLoading && (
                <div className="flex justify-center py-4">
                    <div className="bg-[#1f1f1f] px-6 py-3 rounded-full flex items-center gap-3 border border-gray-800 animate-pulse">
                        <Loader2 className="w-5 h-5 animate-spin text-yellow-500" /><span className="text-sm text-gray-300 font-bold">Analisando documento...</span>
                    </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </main>

        <div ref={messagesEndRef} className="h-40" />

        {/* ÁREA DE UPLOAD NO RODAPÉ */}
        <footer className="absolute bottom-0 left-0 w-full pt-32 pb-12 px-6 flex flex-col items-center pointer-events-none bg-gradient-to-t from-[#121212] via-[#121212]/95 to-transparent z-10">
            <div className="w-full max-w-2xl pointer-events-auto">
                <div className="shadow-[0_10px_40px_rgba(0,0,0,0.5)] rounded-2xl bg-[#1f1f1f]">
                  <input type="file" accept=".pdf" ref={fileInputRef} onChange={handleFileUpload} className="hidden" />
                  <button 
                    onClick={() => fileInputRef.current?.click()} 
                    disabled={isLoading} 
                    className="w-full p-6 border-2 border-dashed border-gray-600 hover:border-yellow-500 rounded-2xl flex flex-col items-center justify-center gap-3 text-gray-400 hover:text-yellow-500 transition-all disabled:opacity-50 cursor-pointer"
                  >
                      <UploadCloud className="w-8 h-8" />
                      <span className="font-bold text-sm tracking-wide">
                        {activeModule === 'inventario' 
                          ? 'Clique aqui para enviar o Inventário (Excel/PDF)' 
                          : 'Clique aqui para enviar o Novo Relatório (PDF)'}
                      </span>
                  </button>
                </div>
            </div>
        </footer>
      </div>
    </div>
  );
}