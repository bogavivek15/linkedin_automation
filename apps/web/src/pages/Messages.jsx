import React, { useState, useEffect } from 'react';
import {
  MessageSquare,
  Send,
  Search,
  MoreHorizontal,
  Video,
  Star,
  Image as ImageIcon,
  Paperclip,
  Smile,
  CheckCircle2,
  Sparkles
} from 'lucide-react';
import { Avatar, AvatarFallback } from '../components/ui/Avatar';
import { getNetworkProfiles, getMessages, sendMessage, getProfile } from '../services/api';

export function MessagesPage() {
  const [profiles, setProfiles] = useState([]);
  const [selectedProfileId, setSelectedProfileId] = useState('a0000000-0000-0000-0000-000000000001');
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [toastMessage, setToastMessage] = useState(null);
  const [userProfile, setUserProfile] = useState(null);

  useEffect(() => {
    getNetworkProfiles().then((profs) => {
      setProfiles(profs || []);
      if (profs && profs.length > 0 && !selectedProfileId) {
        setSelectedProfileId(profs[0].id);
      }
    });
    getProfile().then((p) => setUserProfile(p));
  }, []);

  useEffect(() => {
    if (selectedProfileId) {
      getMessages(selectedProfileId).then((msgs) => {
        setMessages(msgs || []);
      });
    }
  }, [selectedProfileId]);

  async function handleSend() {
    if (!inputText.trim()) return;
    const sent = await sendMessage(selectedProfileId, inputText, false);
    setMessages((prev) => [...prev, sent]);
    setInputText('');
  }

  async function handleInsertAgentDraft() {
    const draftText = `We use LangGraph checkpointing backed by PostgreSQL state tables. When an agent trips an approval gate (like an unverified work authorization claim), the run pauses and notifies the Command Center until explicit human resolution.`;
    setInputText(draftText);
    setToastMessage('Agent grounded answer draft inserted into input field.');
    setTimeout(() => setToastMessage(null), 3000);
  }

  const activeContact = profiles.find((p) => p.id === selectedProfileId);

  return (
    <div className="max-w-[1128px] mx-auto py-6 px-0 sm:px-4">
      {/* Toast */}
      {toastMessage && (
        <div className="fixed bottom-6 left-6 z-50 bg-[#333333] text-white text-sm px-4 py-3 rounded shadow-lg flex items-center gap-2 animate-fade-in">
          <CheckCircle2 className="h-4 w-4 text-green-500" />
          {toastMessage}
        </div>
      )}

      <div className="bg-white border border-[#ebebeb] shadow-[0_1px_2px_rgba(0,0,0,0.08)] rounded-lg flex h-[calc(100vh-140px)] min-h-[600px] overflow-hidden">
        
        {/* Left: Conversations Thread List (320px) */}
        <div className="w-[320px] shrink-0 border-r border-[#ebebeb] flex flex-col bg-white">
          <div className="p-3 border-b border-[#ebebeb] flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-black">Messaging</h2>
              <div className="flex items-center gap-2">
                <button className="h-8 w-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition-colors">
                  <MoreHorizontal className="h-5 w-5 text-gray-500" />
                </button>
                <button className="h-8 w-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition-colors">
                  <MessageSquare className="h-5 w-5 text-gray-500" />
                </button>
              </div>
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-2 h-4 w-4 text-gray-500" />
              <input
                type="text"
                placeholder="Search messages"
                className="h-8 w-full rounded bg-[#eef3f8] pl-9 pr-3 text-sm text-black placeholder:text-gray-600 focus:outline-none focus:ring-1 focus:ring-black/20"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {profiles.map((p) => {
              const isSelected = p.id === selectedProfileId;
              const lastMessage = p.id === 'a0000000-0000-0000-0000-000000000001'
                ? 'Sarah: Thanks for reaching out Vivek! Great to see students...'
                : 'Connect proposal sent';

              return (
                <button
                  key={p.id}
                  onClick={() => setSelectedProfileId(p.id)}
                  className={`w-full p-3 text-left flex items-start gap-3 transition-colors border-l-4 relative ${
                    isSelected ? 'bg-[#f3f2ef] border-green-700' : 'bg-white border-transparent hover:bg-gray-50'
                  }`}
                >
                  <Avatar className="h-12 w-12 shrink-0">
                    <AvatarFallback className="bg-gray-200 text-gray-700 font-bold text-lg">
                      {p.full_name.split(' ').map((n) => n[0]).join('')}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0 flex flex-col justify-center pt-1">
                    <div className="flex items-center justify-between">
                      <span className={`text-sm truncate ${isSelected ? 'font-semibold text-black' : 'font-medium text-gray-800'}`}>
                        {p.full_name}
                      </span>
                      <span className="text-xs text-gray-500">Sep 9</span>
                    </div>
                    <p className={`text-xs truncate ${isSelected ? 'text-black' : 'text-gray-500'}`}>
                      {lastMessage}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right: Active Chat Conversation */}
        <div className="flex-1 flex flex-col bg-white min-w-0">
          
          {/* Active Contact Header */}
          {activeContact && (
            <div className="p-3 border-b border-[#ebebeb] flex items-center justify-between bg-white shrink-0">
              <div className="flex items-center gap-3">
                <div className="flex flex-col">
                  <h3 className="text-base font-semibold text-black hover:text-[#0a66c2] hover:underline cursor-pointer">
                    {activeContact.full_name}
                  </h3>
                  <p className="text-xs text-gray-500 line-clamp-1">{activeContact.headline}</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button className="h-8 w-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition-colors">
                  <Video className="h-5 w-5 text-gray-500" />
                </button>
                <button className="h-8 w-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition-colors">
                  <Star className="h-5 w-5 text-gray-500" />
                </button>
                <button className="h-8 w-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition-colors">
                  <MoreHorizontal className="h-5 w-5 text-gray-500" />
                </button>
              </div>
            </div>
          )}

          {/* Messages Stream */}
          <div className="flex-1 p-4 overflow-y-auto space-y-6">
            {/* Top Profile Summary */}
            {activeContact && (
              <div className="pb-4 border-b border-[#ebebeb] flex flex-col items-center">
                <Avatar className="h-[72px] w-[72px] cursor-pointer hover:underline mb-2">
                  <AvatarFallback className="bg-gray-200 text-gray-700 font-bold text-xl">
                    {activeContact.full_name.split(' ').map((n) => n[0]).join('')}
                  </AvatarFallback>
                </Avatar>
                <h3 className="text-base font-semibold text-black cursor-pointer hover:underline hover:text-[#0a66c2]">
                  {activeContact.full_name}
                </h3>
                <p className="text-sm text-gray-600 text-center max-w-sm mt-1">{activeContact.headline}</p>
              </div>
            )}

            {messages.map((m) => {
              const isMe = m.sender_id === 'user_current_candidate' || m.sender_name === 'You';
              return (
                <div key={m.id} className="flex flex-col">
                  <div className="flex items-start gap-3">
                    <Avatar className="h-10 w-10 shrink-0 mt-1 cursor-pointer">
                      <AvatarFallback className="bg-gray-200 text-gray-700 font-bold text-sm">
                        {isMe 
                          ? (userProfile?.full_name ? userProfile.full_name.split(' ').map((n) => n[0]).join('') : 'Me')
                          : activeContact?.full_name.split(' ').map((n) => n[0]).join('')}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1">
                      <div className="flex items-baseline gap-2 mb-1">
                        <span className="text-sm font-semibold text-black hover:underline cursor-pointer">
                          {isMe ? (userProfile?.full_name || 'You') : activeContact?.full_name}
                        </span>
                        <span className="text-xs text-gray-500">
                          {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <div className="text-sm text-black leading-relaxed whitespace-pre-wrap">
                        {m.body}
                      </div>

                      {/* Evidence Provenance Badge */}
                      {m.evidence_grounding && (
                        <div className="mt-2 inline-flex items-center gap-1.5 px-2 py-1 rounded bg-[#eef3f8] text-xs text-gray-700 border border-[#ebebeb]">
                          <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />
                          <span className="font-semibold text-gray-600">Agent Verified:</span>
                          {m.evidence_grounding}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Agent Draft Recommendation Banner */}
          <div className="px-4 py-3 bg-[#eef3f8] border-t border-[#ebebeb] flex items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-[#0a66c2] text-sm font-semibold">
              <Sparkles className="h-4 w-4 text-amber-500 shrink-0" />
              <span className="truncate">
                Agent synthesized answer regarding LangGraph state checkpointing.
              </span>
            </div>
            <button
              className="shrink-0 bg-white border border-[#0a66c2] text-[#0a66c2] font-semibold text-xs px-3 py-1.5 rounded-full hover:bg-blue-50 transition-colors"
              onClick={handleInsertAgentDraft}
            >
              Insert Draft
            </button>
          </div>

          {/* Message Input Box */}
          <div className="p-3 border-t border-[#ebebeb] bg-[#f9fafb] flex flex-col gap-2">
            <div className="bg-white border border-gray-400 rounded-lg focus-within:border-gray-600 focus-within:ring-1 focus-within:ring-gray-600 overflow-hidden flex flex-col">
              <textarea
                placeholder="Write a message..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                className="w-full min-h-[80px] max-h-[160px] p-3 text-sm text-black resize-none focus:outline-none"
              />
              <div className="p-2 border-t border-[#ebebeb] flex items-center justify-between bg-[#f9fafb]">
                <div className="flex items-center gap-1">
                  <button className="h-8 w-8 rounded-full hover:bg-gray-200 flex items-center justify-center transition-colors">
                    <ImageIcon className="h-5 w-5 text-gray-500" />
                  </button>
                  <button className="h-8 w-8 rounded-full hover:bg-gray-200 flex items-center justify-center transition-colors">
                    <Paperclip className="h-5 w-5 text-gray-500" />
                  </button>
                  <button className="h-8 w-8 rounded-full hover:bg-gray-200 flex items-center justify-center transition-colors">
                    <Smile className="h-5 w-5 text-gray-500" />
                  </button>
                </div>
                <button 
                  onClick={handleSend} 
                  disabled={!inputText.trim()}
                  className={`px-4 py-1.5 rounded-full font-semibold text-sm transition-colors ${
                    inputText.trim() ? 'bg-[#0a66c2] hover:bg-[#004182] text-white' : 'bg-[#eef3f8] text-gray-400 cursor-not-allowed'
                  }`}
                >
                  Send
                </button>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
