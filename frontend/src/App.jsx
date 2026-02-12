import { useState, useRef, useEffect } from 'react';
import { Send, Menu, MessageSquare, Loader2, FileText, ChevronRight, Copy, Check, Download } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import logo from './Logo.jpeg'; 

export default function App() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [options, setOptions] = useState([]); 
  const [copiedIndex, setCopiedIndex] = useState(null);
  const messagesEndRef = useRef(null);

  const hasStarted = messages.length > 0;

  const tools = [
    { icon: MessageSquare, name: 'Nova análise', description: 'Limpar e iniciar nova conversa' },
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  useEffect(scrollToBottom, [messages, options]);

  const handleSubmit = async (text) => {
    const messageText = text || input;
    if (!messageText.trim()) return;

    if (!text) {
        setMessages(prev => [...prev, { role: 'user', content: messageText }]);
    }
    
    setInput('');
    setOptions([]); 
    setIsLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: messageText }),
      });

      const data = await response.json();

      if (data.options) {
        setMessages(prev => [...prev, { role: 'assistant', content: data.reply }]);
        setOptions(data.options); 
      } else {
        // Agora salvamos também o pdf_name se ele vier
        setMessages(prev => [...prev, { 
            role: 'assistant', 
            content: data.reply || "Erro: Sem resposta.",
            pdfName: data.pdf_name // Salva o nome para o download
        }]);
      }

    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: "❌ Erro de conexão." }]);
    } finally {
      setIsLoading(false);
    }
  };

  const formatForWhatsapp = (text) => {
    return text
        .replace(/^### /gm, "\n")
        .replace(/^> /gm, "\n\n")
        .replace(/^- /gm, "•  ")
        .replace(/---/g, "━━━━━━━━━━━━━━━")
        .replace(/\*\*/g, "")
        .replace(/\*/g, "");
  };

  const copyToClipboard = (text, index) => {
    const whatsappText = formatForWhatsapp(text);
    navigator.clipboard.writeText(whatsappText);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  return (
    <div className="min-h-screen bg-[#121212] flex font-sans text-gray-100 selection:bg-yellow-500/30 overflow-hidden">
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? 'w-72' : 'w-0'} bg-[#0a0a0a] border-r border-gray-800 transition-all duration-300 overflow-hidden flex flex-col z-20`}>
        <div className="p-8 border-b border-gray-800 flex justify-center bg-black/20">
          <img src={logo} alt="S Consult" className="h-20 object-contain drop-shadow-2xl" />
        </div>
        
        <div className="flex-1 overflow-y-auto p-4">
          <h3 className="text-[10px] font-bold text-gray-500 uppercase mb-4 tracking-widest pl-2">Ferramentas</h3>
          <div className="space-y-2">
            {tools.map((tool, index) => (
              <button
                key={index}
                onClick={() => {setMessages([]); setOptions([]); setInput('');}}
                className="w-full flex items-center gap-4 p-3 rounded-lg hover:bg-[#1f1f1f] border border-transparent hover:border-gray-700 transition-all text-left group"
              >
                <div className="p-2 bg-[#1a1a1a] rounded-md group-hover:bg-yellow-500/10 group-hover:text-yellow-500 transition-colors">
                    <tool.icon className="w-5 h-5 text-gray-400 group-hover:text-yellow-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-gray-200 text-sm font-semibold group-hover:text-white">{tool.name}</div>
                  <div className="text-gray-600 text-xs truncate">{tool.description}</div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-screen relative bg-[#121212]">
        <header className="absolute top-4 left-4 z-10">
            <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-2 bg-[#1f1f1f] rounded-lg text-white hover:bg-gray-700 border border-gray-700 shadow-lg transition-colors">
                <Menu className="w-5 h-5" />
            </button>
        </header>

        {/* Chat Area */}
        <main className={`flex-1 overflow-y-auto px-4 md:px-10 transition-all duration-500 ${hasStarted ? 'pt-20 pb-40' : 'pt-0 pb-0'}`}>
          {!hasStarted && (
            <div className="absolute top-[10%] left -0 w-full flex flex-col items-center justify-center px-4 animate-in fade-in zoom-in duration-500">
                <div className="w-20 h-20 bg-[#1f1f1f] rounded-3xl flex items-center justify-center mb-6 border border-gray-800 shadow-[0_0_50px_rgba(234,179,8,0.1)]">
                    <FileText className="w-10 h-10 text-yellow-500" />
                </div>
                <h1 className="text-4xl md:text-5xl font-bold text-white mb-4 text-center tracking-tight">Portal S Consult</h1>
                <p className="text-gray-400 text-lg max-w-lg text-center leading-relaxed">
                   Inteligência Artificial para análise de LVCs.
                </p>
            </div>
          )}

          {hasStarted && (
            <div className="max-w-4xl mx-auto space-y-8">
              {messages.map((message, index) => (
                <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-in slide-in-from-bottom-4 duration-500`}>
                  <div className={`w-full ${message.role === 'user' ? 'max-w-md' : 'max-w-4xl'}`}>
                    {message.role === 'user' ? (
                        <div className="bg-[#2f2f2f] text-white p-4 rounded-2xl rounded-br-none border border-gray-700 shadow-lg ml-auto">
                            {message.content}
                        </div>
                    ) : (
                        <div className="bg-[#1a1a1a] border border-gray-800 rounded-2xl p-6 md:p-8 shadow-2xl relative overflow-hidden group">
                            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-yellow-600 via-yellow-400 to-yellow-600"></div>
                            
                            {/* Botão Copiar WhatsApp */}
                            <button 
                                onClick={() => copyToClipboard(message.content, index)}
                                className="absolute top-4 right-4 p-2 bg-[#252525] hover:bg-yellow-500 hover:text-black rounded-lg transition-colors border border-gray-700 flex items-center gap-2 z-10"
                                title="Copiar limpo para WhatsApp"
                            >
                                {copiedIndex === index ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                                <span className="text-xs font-bold">{copiedIndex === index ? "Copiado!" : "WhatsApp"}</span>
                            </button>

                            {/* Conteúdo do Relatório */}
                            <div className="prose prose-invert max-w-none mt-4">
                                <ReactMarkdown components={{
                                    h3: ({node, ...props}) => <h3 className="text-2xl font-bold text-yellow-400 mt-8 mb-4 border-b border-gray-700 pb-2" {...props} />,
                                    ul: ({node, ...props}) => <ul className="space-y-2 my-4" {...props} />,
                                    li: ({node, ...props}) => <li className="text-gray-300 ml-4 list-disc marker:text-yellow-500" {...props} />,
                                    blockquote: ({node, ...props}) => (
                                        <div className="bg-[#252525] border-l-4 border-yellow-500 rounded-r-lg p-4 my-6 shadow-md">
                                            <div className="italic text-gray-300 not-italic" {...props} />
                                        </div>
                                    ),
                                    strong: ({node, ...props}) => <strong className="text-white font-bold" {...props} />,
                                }}>
                                    {message.content}
                                </ReactMarkdown>
                            </div>

                            {/* BOTÃO DOWNLOAD PDF (Discreto no rodapé) */}
                            {message.pdfName && (
                                <div className="mt-8 pt-4 border-t border-gray-800 flex justify-end">
                                    <a 
                                        href={`http://127.0.0.1:8000/download?filename=${encodeURIComponent(message.pdfName)}`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="flex items-center gap-2 text-xs font-medium text-gray-500 hover:text-yellow-500 transition-colors opacity-70 hover:opacity-100"
                                    >
                                        <Download className="w-4 h-4" />
                                        Baixar PDF Original ({message.pdfName})
                                    </a>
                                </div>
                            )}
                        </div>
                    )}
                  </div>
                </div>
              ))}

              {options.length > 0 && (
                 <div className="flex flex-col gap-3 max-w-md mx-auto animate-in fade-in pb-10">
                    <p className="text-center text-gray-400 text-sm mb-2">Selecione o arquivo correto:</p>
                    {options.map((opt, idx) => (
                        <button
                            key={idx}
                            onClick={() => handleSubmit(opt)}
                            className="flex items-center justify-between p-4 bg-[#2f2f2f] hover:bg-yellow-500 hover:text-black border border-gray-700 hover:border-yellow-500 rounded-xl transition-all group"
                        >
                            <span className="font-medium truncate">{opt}</span>
                            <ChevronRight className="w-5 h-5 text-gray-500 group-hover:text-black" />
                        </button>
                    ))}
                 </div>
              )}
              
              {isLoading && (
                <div className="flex justify-center py-8">
                    <div className="bg-[#1f1f1f] px-6 py-3 rounded-full flex items-center gap-3 border border-gray-800 shadow-xl animate-pulse">
                        <Loader2 className="w-5 h-5 animate-spin text-yellow-500" />
                        <span className="text-sm text-gray-300 font-medium">Analisando engenharia...</span>
                    </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </main>

        <div className={`absolute left-0 w-full px-4 md:px-10 transition-all duration-700 ease-in-out z-20 ${
            hasStarted ? 'bottom-8' : 'top-[50%] -translate-y-1/2'
        }`}>
            <div className={`max-w-3xl mx-auto relative group transition-all duration-700 ${!hasStarted ? 'scale-110' : 'scale-100'}`}>
                <div className="absolute inset-0 bg-yellow-500/10 rounded-full blur-2xl opacity-0 group-focus-within:opacity-100 transition-all duration-700"></div>
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
                  disabled={isLoading}
                  placeholder={hasStarted ? "Faça outra pesquisa..." : "Pesquisar trecho ou código (Ex: arraial)"}
                  className="w-full px-8 py-5 pr-16 rounded-2xl border border-gray-700 bg-[#1a1a1a]/95 backdrop-blur-md text-white placeholder-gray-500 focus:outline-none focus:border-yellow-500 focus:ring-1 focus:ring-yellow-500 shadow-2xl relative z-10 transition-all text-lg"
                />
                <button
                  onClick={() => handleSubmit()}
                  disabled={!input.trim() || isLoading}
                  className={`absolute right-4 top-1/2 -translate-y-1/2 p-3 rounded-xl transition-all z-20 ${
                    input.trim() && !isLoading
                      ? 'bg-yellow-500 text-black hover:bg-yellow-400 hover:scale-105 shadow-lg' 
                      : 'bg-transparent text-gray-600 cursor-not-allowed'
                  }`}
                >
                  {isLoading ? <Loader2 className="w-5 h-5 animate-spin"/> : <Send className="w-5 h-5" />}
                </button>
            </div>
        </div>
      </div>
    </div>
  );
}