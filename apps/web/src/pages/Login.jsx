import React, { useState, useRef } from 'react';
import { Zap, ArrowRight, Shield, Cpu, Upload, FileText } from 'lucide-react';
import { startOrchestrator, setAuthToken } from '../services/api';

export function LoginPage({ onLogin }) {
  const [step, setStep] = useState('login'); // 'login' | 'agent-setup'
  const [isConnecting, setIsConnecting] = useState(false);
  
  // Form State
  const [resumeText, setResumeText] = useState('');
  const [targetRoles, setTargetRoles] = useState('');
  const [locations, setLocations] = useState('');
  const [resumeFile, setResumeFile] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setResumeFile(file);
      setResumeText(`[Mock Extracted Content from ${file.name}]\n\nSenior Software Engineer with 5 years of experience...`);
    }
  };

  const handleStandardLogin = (e) => {
    e.preventDefault();
    // Generate a demo user token (in production, this would come from actual auth)
    const demoUserId = crypto.randomUUID();
    const demoToken = demoUserId; // Backend accepts UUID as token in demo mode
    setAuthToken(demoToken, demoUserId);
    onLogin();
  };

  const handleConnectAgents = async (e) => {
    e.preventDefault();
    setIsConnecting(true);
    
    // Generate user token before making API calls
    const userId = crypto.randomUUID();
    const token = userId; // Backend accepts UUID as token in demo mode
    setAuthToken(token, userId);
    
    try {
      await startOrchestrator(targetRoles, locations, resumeText);
      onLogin(); // transition to main app
    } catch (err) {
      console.error('Agent connection error:', err);
      // Still transition to main app even if orchestrator fails
      onLogin();
    }
  };

  return (
    <div className="min-h-screen bg-[#f3f2ef] flex flex-col items-center justify-center p-4 font-sans text-black/90 selection:bg-[#0a66c2]/30">
      
      {/* Brand Header */}
      <div className="mb-8 flex items-center gap-2">
        <div className="bg-[#0a66c2] text-white p-1.5 rounded font-bold text-xl leading-none">in</div>
        <span className="text-2xl font-bold tracking-tight text-[#0a66c2]">CareerOS</span>
      </div>

      <div className="bg-white rounded-lg shadow-[0_4px_12px_rgba(0,0,0,0.15)] w-full max-w-md overflow-hidden animate-fade-in border border-[#ebebeb]">
        
        {step === 'login' && (
          <div className="p-8">
            <h1 className="text-3xl font-semibold mb-2">Sign in</h1>
            <p className="text-sm text-gray-600 mb-8">Stay updated on your professional world</p>

            <form onSubmit={handleStandardLogin} className="space-y-4">
              <div>
                <input 
                  type="email" 
                  placeholder="Email or phone" 
                  className="w-full px-4 py-3 rounded border border-gray-400 focus:border-[#0a66c2] focus:ring-1 focus:ring-[#0a66c2] outline-none transition-colors"
                  required
                />
              </div>
              <div>
                <input 
                  type="password" 
                  placeholder="Password" 
                  className="w-full px-4 py-3 rounded border border-gray-400 focus:border-[#0a66c2] focus:ring-1 focus:ring-[#0a66c2] outline-none transition-colors"
                  required
                />
              </div>
              
              <div className="pt-2">
                <button 
                  type="submit" 
                  className="w-full bg-[#0a66c2] text-white rounded-full py-3.5 font-semibold text-base hover:bg-[#004182] transition-colors"
                >
                  Sign in
                </button>
              </div>
            </form>

            <div className="mt-8 relative flex items-center justify-center">
              <div className="border-t border-gray-300 w-full absolute"></div>
              <span className="bg-white px-4 text-sm text-gray-500 relative z-10">or</span>
            </div>

            <div className="mt-8 space-y-4">
              <button 
                onClick={() => setStep('agent-setup')}
                className="w-full bg-white text-[#0a66c2] border border-[#0a66c2] rounded-full py-3.5 font-semibold text-base hover:bg-blue-50 transition-colors flex items-center justify-center gap-2 group"
              >
                <Zap className="h-5 w-5 group-hover:text-amber-500 transition-colors" />
                Connect Agents (AI Co-pilot)
              </button>
              <p className="text-xs text-center text-gray-500 mt-2 px-4">
                Delegate your job search, networking, and applications to deterministic autonomous agents.
              </p>
            </div>
          </div>
        )}

        {step === 'agent-setup' && (
          <div className="p-8 animate-fade-in">
            <div className="flex items-center gap-3 mb-6 border-b border-[#ebebeb] pb-4">
              <div className="bg-[#eef3f8] p-2 rounded-full text-[#0a66c2]">
                <Cpu className="h-6 w-6" />
              </div>
              <div>
                <h2 className="text-xl font-semibold">Initialize Career Agents</h2>
                <p className="text-xs text-gray-600 mt-1">Provide context to ground your AI co-pilot.</p>
              </div>
            </div>

            <form onSubmit={handleConnectAgents} className="space-y-5">
              
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1 flex items-center gap-2">
                  <Shield className="h-4 w-4 text-green-600" /> Target Roles
                </label>
                <input 
                  type="text" 
                  value={targetRoles}
                  onChange={(e) => setTargetRoles(e.target.value)}
                  placeholder="e.g. Senior Software Engineer, ML Engineer" 
                  className="w-full px-3 py-2.5 rounded border border-gray-300 focus:border-[#0a66c2] focus:ring-1 focus:ring-[#0a66c2] outline-none text-sm transition-colors"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Preferred Locations</label>
                <input 
                  type="text" 
                  value={locations}
                  onChange={(e) => setLocations(e.target.value)}
                  placeholder="e.g. San Francisco, Remote, London" 
                  className="w-full px-3 py-2.5 rounded border border-gray-300 focus:border-[#0a66c2] focus:ring-1 focus:ring-[#0a66c2] outline-none text-sm transition-colors"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1 flex items-center gap-2">
                  <Upload className="h-4 w-4 text-gray-500" /> Grounding Resume
                </label>
                <p className="text-[10px] text-gray-500 mb-2 leading-tight">
                  Upload your resume or paste the text. Agents will strictly construct applications based on this evidence.
                </p>
                
                {resumeFile ? (
                  <div className="flex items-center justify-between p-3 border border-green-300 bg-green-50 rounded mb-2">
                    <div className="flex items-center gap-2 text-green-700 text-sm font-semibold">
                      <FileText className="h-4 w-4" />
                      {resumeFile.name}
                    </div>
                    <button type="button" onClick={() => {setResumeFile(null); setResumeText('');}} className="text-xs text-gray-500 hover:text-gray-700">Remove</button>
                  </div>
                ) : (
                  <div 
                    onClick={() => fileInputRef.current?.click()}
                    className="border-2 border-dashed border-gray-300 rounded-lg p-6 flex flex-col items-center justify-center text-gray-500 hover:bg-gray-50 hover:border-[#0a66c2] hover:text-[#0a66c2] transition-colors cursor-pointer mb-2"
                  >
                    <Upload className="h-6 w-6 mb-2" />
                    <span className="text-sm font-semibold">Click to upload PDF or DOCX</span>
                    <span className="text-xs mt-1">or drag and drop</span>
                  </div>
                )}
                
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  className="hidden" 
                  accept=".pdf,.doc,.docx,.txt"
                  onChange={handleFileChange} 
                />

                {!resumeFile && (
                  <>
                    <div className="flex items-center my-2">
                      <div className="border-t border-gray-200 flex-1"></div>
                      <span className="px-2 text-xs text-gray-400">or paste text</span>
                      <div className="border-t border-gray-200 flex-1"></div>
                    </div>
                    <textarea 
                      value={resumeText}
                      onChange={(e) => setResumeText(e.target.value)}
                      placeholder="Paste your current resume or LinkedIn profile summary here..." 
                      className="w-full px-3 py-2.5 rounded border border-gray-300 focus:border-[#0a66c2] focus:ring-1 focus:ring-[#0a66c2] outline-none text-sm transition-colors min-h-[100px] resize-none"
                      required={!resumeFile}
                    ></textarea>
                  </>
                )}
              </div>

              <div className="pt-4 flex gap-3">
                <button 
                  type="button"
                  onClick={() => setStep('login')}
                  className="w-1/3 border border-gray-500 text-gray-600 rounded-full py-2.5 font-semibold text-sm hover:bg-gray-50 transition-colors"
                  disabled={isConnecting}
                >
                  Back
                </button>
                <button 
                  type="submit" 
                  className="w-2/3 bg-[#0a66c2] text-white rounded-full py-2.5 font-semibold text-sm hover:bg-[#004182] transition-colors flex items-center justify-center gap-2"
                  disabled={isConnecting}
                >
                  {isConnecting ? (
                    <span className="animate-pulse">Starting Orchestrator...</span>
                  ) : (
                    <>Start Agents <ArrowRight className="h-4 w-4" /></>
                  )}
                </button>
              </div>

            </form>
          </div>
        )}

      </div>
      
      <div className="mt-8 text-xs text-gray-500 flex gap-4">
        <a href="#" className="hover:text-[#0a66c2] hover:underline">User Agreement</a>
        <a href="#" className="hover:text-[#0a66c2] hover:underline">Privacy Policy</a>
        <a href="#" className="hover:text-[#0a66c2] hover:underline">Community Guidelines</a>
      </div>
    </div>
  );
}
