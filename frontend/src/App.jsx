import { useState, useRef, useEffect } from 'react';
import { Send, Menu, Loader2, FileText, ChevronRight, Copy, Check, Download, LogOut, Search, UploadCloud } from 'lucide-react';
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

  const [activeModule, setActiveModule] = useState('nuvem'); // 'nuvem' ou 'inventario'
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [options, setOptions] = useState([]); 
  const [copiedIndex, setCopiedIndex] = useState(null);
  
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const hasStarted = messages.length > 0;
  
  // ⚠️ ATENÇÃO AQUI: Se estiver rodando no seu PC, deixe 127.0.0.1. Se for subir pro Render, mude!
  const API_URL = "https://s-consult-backend.onrender.com";

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, options, isLoading]);

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
    setMessages([]);
    setOptions([]);
    setInput('');
  };

  // --- SERVIÇO 1: BUSCAR NO FIREBASE ---
  const handleCloudSearch = async (text) => {
    const messageText = text || input;
    if (!messageText.trim()) return;

    if (!text) setMessages(prev => [...prev, { role: 'user', content: messageText }]);
    
    setInput('');
    setOptions([]); 
    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: messageText }),
      });

      const data = await response.json();

      if (data.options) {
        setMessages(prev => [...prev, { role: 'assistant', content: data.reply }]);
        setOptions(data.options); 
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: data.reply || "Sem resposta.", pdfName: data.pdf_name }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: "❌ Erro de conexão. Verifique se o backend Python está rodando." }]);
    } finally {
      setIsLoading(false);
    }
  };

  // --- SERVIÇO 2: LER TABELAS (UPLOAD) ---
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setMessages(prev => [...prev, { role: 'user', content: `📄 Inventário Enviado:\n${file.name}` }]);
    setIsLoading(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_URL}/upload-pdf`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply, pdfName: data.pdf_name }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: "❌ Falha ao conectar com o servidor para envio do PDF." }]);
    } finally {
      setIsLoading(false);
      event.target.value = null;
    }
  };

  const copyToClipboard = (text, index) => {
    const limpo = text.replace(/^### /gm, "\n").replace(/^> /gm, "\n\n").replace(/^- /gm, "•  ").replace(/---/g, "━━━━━━━━━━━━━━━").replace(/\*\*/g, "").replace(/\*/g, "");
    navigator.clipboard.writeText(limpo);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

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

  return (
    <div className="min-h-screen bg-[#121212] flex font-sans text-gray-100 selection:bg-yellow-500/30 overflow-hidden">
      
      {/* SIDEBAR SEPARADA EM MÓDULOS */}
      <aside className={`${sidebarOpen ? 'w-72' : 'w-0'} bg-[#0a0a0a] border-r border-gray-800 transition-all duration-300 overflow-hidden flex flex-col shrink-0 z-20`}>
        <div className="p-8 border-b border-gray-800 flex justify-center bg-black/20">
          <img src={logo} alt="S Consult" className="h-20 object-contain drop-shadow-2xl" />
        </div>
        
        <div className="flex-1 overflow-y-auto p-4">
          <h3 className="text-[10px] font-bold text-gray-500 uppercase mb-4 tracking-widest pl-2">Módulos do Sistema</h3>
          <div className="space-y-3">
            
            <button onClick={() => switchModule('nuvem')} className={`w-full flex items-center gap-4 p-4 rounded-xl transition-all border text-left ${activeModule === 'nuvem' ? 'bg-[#1f1f1f] border-yellow-500 text-white' : 'border-transparent text-gray-400 hover:bg-[#1a1a1a]'}`}>
              <div className={`p-2 rounded-lg ${activeModule === 'nuvem' ? 'bg-yellow-500/10 text-yellow-500' : 'bg-gray-800'}`}><Search className="w-5 h-5" /></div>
              <div><div className="text-sm font-bold">Consultar Nuvem</div><div className="text-[10px] text-gray-500">Buscar Relatórios Prontos</div></div>
            </button>

            <button onClick={() => switchModule('inventario')} className={`w-full flex items-center gap-4 p-4 rounded-xl transition-all border text-left ${activeModule === 'inventario' ? 'bg-[#1f1f1f] border-yellow-500 text-white' : 'border-transparent text-gray-400 hover:bg-[#1a1a1a]'}`}>
              <div className={`p-2 rounded-lg ${activeModule === 'inventario' ? 'bg-yellow-500/10 text-yellow-500' : 'bg-gray-800'}`}><UploadCloud className="w-5 h-5" /></div>
              <div><div className="text-sm font-bold">Processar Inventário</div><div className="text-[10px] text-gray-500">Ler Tabelas de PDF Local</div></div>
            </button>

          </div>
        </div>

        <div className="p-4 border-t border-gray-800">
           <button onClick={handleLogout} className="w-full flex items-center gap-3 p-3 text-gray-500 hover:text-red-500 rounded-lg transition-all text-sm font-bold uppercase tracking-tighter">
             <LogOut className="w-4 h-4" /> Sair do Sistema
           </button>
        </div>
      </aside>

      {/* ÁREA PRINCIPAL */}
      <div className="flex-1 flex flex-col h-screen relative bg-[#121212]">
        <header className="h-16 flex items-center px-6 border-b border-gray-800/60 bg-[#0a0a0a] sticky top-0 z-10">
            <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-2 mr-4 bg-[#1f1f1f] rounded-lg text-white hover:bg-gray-700 border border-gray-700"><Menu className="w-5 h-5" /></button>
            <span className="text-xs font-black text-gray-500 uppercase tracking-[0.3em]">
              {activeModule === 'nuvem' ? 'MÓDULO: PESQUISA EM BANCO DE DADOS' : 'MÓDULO: LEITURA NATIVA DE INVENTÁRIOS'}
            </span>
        </header>

        {/* CHAT AREA */}
        <main className={`flex-1 overflow-y-auto px-4 md:px-10 transition-all duration-500 pb-32 pt-10`}>
          {!hasStarted ? (
            <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
                <div className="w-20 h-20 bg-[#1f1f1f] rounded-3xl flex items-center justify-center mb-6 border border-gray-800 shadow-[0_0_50px_rgba(234,179,8,0.1)]">
                    {activeModule === 'nuvem' ? <Search className="w-10 h-10 text-yellow-500" /> : <FileText className="w-10 h-10 text-yellow-500" />}
                </div>
                <h1 className="text-4xl font-bold text-white mb-2">
                  {activeModule === 'nuvem' ? 'Pesquisa de Relatórios' : 'Analisador de Tabelas'}
                </h1>
                <p className="text-gray-400 text-sm max-w-sm">
                  {activeModule === 'nuvem' ? 'Digite o nome do trecho para buscar documentos arquivados no sistema.' : 'Faça o upload de um inventário bruto. A IA fará a leitura das tabelas.'}
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
                            <ReactMarkdown components={{
                                h3: ({node, ...props}) => <h3 className="text-xl font-bold text-yellow-400 mt-8 mb-4 border-b border-gray-700 pb-2 uppercase" {...props} />,
                                blockquote: ({node, ...props}) => (
                                    <div className="bg-[#252525] border-l-4 border-yellow-500 rounded-r-lg p-4 my-4 shadow-md">
                                        <div className="italic text-gray-300" {...props} />
                                    </div>
                                ),
                                ul: ({node, ...props}) => <ul className="space-y-2 my-2" {...props} />,
                                li: ({node, ...props}) => <li className="text-gray-300 ml-4 list-disc marker:text-yellow-500" {...props} />,
                                strong: ({node, ...props}) => <strong className="text-white font-bold" {...props} />
                            }}>
                                {message.content}
                            </ReactMarkdown>
                        )}
                    </div>

                    {message.pdfName && message.role === 'assistant' && !message.content.includes("❌") && (
                        <div className="mt-8 pt-4 border-t border-gray-800 flex justify-end">
                            <a href={`${API_URL}/download?filename=${encodeURIComponent(message.pdfName)}`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-xs font-medium text-gray-500 hover:text-yellow-500 transition-colors">
                                <Download className="w-4 h-4" /> Baixar PDF Original
                            </a>
                        </div>
                    )}
                  </div>
                </div>
              ))}

              {options.length > 0 && activeModule === 'nuvem' && (
                 <div className="flex flex-col gap-3 max-w-md mx-auto">
                    <p className="text-center text-gray-400 text-sm mb-2">Selecione o arquivo correto:</p>
                    {options.map((opt, idx) => (
                        <button key={idx} onClick={() => handleCloudSearch(opt)} className="flex items-center justify-between p-4 bg-[#2f2f2f] hover:bg-yellow-500 hover:text-black border border-gray-700 rounded-xl transition-all">
                            <span className="font-medium truncate">{opt}</span><ChevronRight className="w-5 h-5" />
                        </button>
                    ))}
                 </div>
              )}
              
              {isLoading && (
                <div className="flex justify-center py-4">
                    <div className="bg-[#1f1f1f] px-6 py-3 rounded-full flex items-center gap-3 border border-gray-800 animate-pulse">
                        <Loader2 className="w-5 h-5 animate-spin text-yellow-500" /><span className="text-sm text-gray-300 font-bold">Processando engenharia...</span>
                    </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </main>

        {/* O "EMPURRÃOZINHO" DO TEXTO VEM AQUI! (Isso evita que o texto fique atrás da barra) */}
        <div ref={messagesEndRef} className="h-40" />

        {/* RODAPÉ DINÂMICO COM O EFEITO "NÉVOA" */}
        <footer className="absolute bottom-0 left-0 w-full pt-32 pb-12 px-6 flex flex-col items-center pointer-events-none bg-gradient-to-t from-[#121212] via-[#121212]/95 to-transparent z-10">
            {/* max-w-2xl deixa a caixa mais contida no centro da tela */}
            <div className="w-full max-w-2xl pointer-events-auto">
                {activeModule === 'nuvem' ? (
                  <div className="relative shadow-[0_10px_40px_rgba(0,0,0,0.5)] rounded-2xl">
                    <input 
                      value={input} 
                      onChange={(e) => setInput(e.target.value)} 
                      onKeyDown={(e) => e.key === 'Enter' && handleCloudSearch()} 
                      disabled={isLoading} 
                      placeholder="Pesquisar trecho no banco de dados..." 
                      className="w-full px-6 py-5 pr-16 rounded-2xl border border-gray-700 bg-[#1f1f1f] text-white outline-none focus:border-yellow-500 shadow-2xl transition-all" 
                    />
                    <button 
                      onClick={() => handleCloudSearch()} 
                      disabled={!input.trim() || isLoading} 
                      className="absolute right-3 top-1/2 -translate-y-1/2 p-3 rounded-xl bg-yellow-500 text-black hover:scale-105 disabled:opacity-50 disabled:hover:scale-100 transition-transform"
                    >
                      <Send className="w-5 h-5" />
                    </button>
                  </div>
                ) : (
                  <div className="shadow-[0_10px_40px_rgba(0,0,0,0.5)] rounded-2xl bg-[#1f1f1f]">
                    <input type="file" accept=".pdf" ref={fileInputRef} onChange={handleFileUpload} className="hidden" />
                    <button 
                      onClick={() => fileInputRef.current?.click()} 
                      disabled={isLoading} 
                      className="w-full p-6 border-2 border-dashed border-gray-600 hover:border-yellow-500 rounded-2xl flex flex-col items-center justify-center gap-3 text-gray-400 hover:text-yellow-500 transition-all disabled:opacity-50 cursor-pointer"
                    >
                        <UploadCloud className="w-8 h-8" />
                        <span className="font-bold text-sm tracking-wide">Clique aqui para enviar o PDF de Inventário</span>
                    </button>
                  </div>
                )}
            </div>
        </footer>
      </div>
    </div>
  );
}
