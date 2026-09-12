import React, { useState, useEffect } from 'react';
import {
  Users,
  Check,
  X,
  Search,
  Building2,
  MapPin,
  UserPlus,
  ChevronRight,
  BookOpen,
  CalendarDays,
  FileText,
  Hash,
  CheckCircle2,
} from 'lucide-react';
import { Avatar, AvatarFallback } from '../components/ui/Avatar';
import { getNetworkProfiles, getAgentProposals, sendConnectionRequest } from '../services/api';

export function NetworkPage({ onNavigate }) {
  const [profiles, setProfiles] = useState([]);
  const [proposals, setProposals] = useState([]);
  const [sentMap, setSentMap] = useState({});
  const [searchQuery, setSearchQuery] = useState('');
  const [toastMessage, setToastMessage] = useState(null);

  useEffect(() => {
    Promise.all([getNetworkProfiles(), getAgentProposals()]).then(([profs, props]) => {
      setProfiles(profs || []);
      setProposals(props || []);
    });
  }, []);

  async function handleApproveProposal(proposal) {
    await sendConnectionRequest(
      proposal.target_profile_id,
      proposal.proposed_note,
      true,
      proposal.evidence_citations.join('; ')
    );
    setSentMap((prev) => ({ ...prev, [proposal.target_profile_id]: true }));
    setProposals((prev) => prev.filter((p) => p.target_profile_id !== proposal.target_profile_id));
    setToastMessage(`Outreach approved! Invitation sent to ${proposal.target_name}.`);
    setTimeout(() => setToastMessage(null), 3500);
  }

  function handleDismissProposal(targetId) {
    setProposals((prev) => prev.filter((p) => p.target_profile_id !== targetId));
  }

  async function handleDirectConnect(profile) {
    await sendConnectionRequest(
      profile.id,
      `Hi ${profile.full_name.split(' ')[0]}, I would love to connect!`,
      false
    );
    setSentMap((prev) => ({ ...prev, [profile.id]: true }));
    setToastMessage(`Connection request sent to ${profile.full_name}.`);
    setTimeout(() => setToastMessage(null), 3000);
  }

  const filteredProfiles = profiles.filter((p) => {
    const matchesSearch =
      p.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.headline.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (p.company && p.company.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesSearch;
  });

  return (
    <div className="max-w-[1128px] mx-auto py-6 px-0 sm:px-4">
      {/* Toast Alert */}
      {toastMessage && (
        <div className="fixed bottom-6 left-6 z-50 bg-[#333333] text-white text-sm px-4 py-3 rounded shadow-lg flex items-center gap-2 animate-fade-in">
          <CheckCircle2 className="h-4 w-4 text-green-500" />
          {toastMessage}
        </div>
      )}

      <div className="flex flex-col lg:flex-row gap-6">
        
        {/* Left Column: Manage my network (225px) */}
        <div className="hidden lg:block w-[225px] shrink-0 space-y-2">
          <div className="rounded-lg bg-white border border-[#ebebeb] shadow-[0_1px_2px_rgba(0,0,0,0.08)] overflow-hidden">
            <h2 className="text-base font-semibold text-black px-4 py-3 border-b border-[#ebebeb]">
              Manage my network
            </h2>
            <div className="py-2">
              <button className="w-full px-4 py-2 flex items-center justify-between text-gray-500 hover:bg-[#f3f2ef] hover:text-black transition-colors">
                <div className="flex items-center gap-3">
                  <Users className="h-5 w-5" />
                  <span className="text-sm font-semibold">Connections</span>
                </div>
                <span className="text-sm">500+</span>
              </button>
              <button className="w-full px-4 py-2 flex items-center justify-between text-gray-500 hover:bg-[#f3f2ef] hover:text-black transition-colors">
                <div className="flex items-center gap-3">
                  <UserPlus className="h-5 w-5" />
                  <span className="text-sm font-semibold">Following & followers</span>
                </div>
              </button>
              <button className="w-full px-4 py-2 flex items-center justify-between text-gray-500 hover:bg-[#f3f2ef] hover:text-black transition-colors">
                <div className="flex items-center gap-3">
                  <Users className="h-5 w-5" />
                  <span className="text-sm font-semibold">Groups</span>
                </div>
              </button>
              <button className="w-full px-4 py-2 flex items-center justify-between text-gray-500 hover:bg-[#f3f2ef] hover:text-black transition-colors">
                <div className="flex items-center gap-3">
                  <CalendarDays className="h-5 w-5" />
                  <span className="text-sm font-semibold">Events</span>
                </div>
              </button>
              <button className="w-full px-4 py-2 flex items-center justify-between text-gray-500 hover:bg-[#f3f2ef] hover:text-black transition-colors">
                <div className="flex items-center gap-3">
                  <FileText className="h-5 w-5" />
                  <span className="text-sm font-semibold">Pages</span>
                </div>
              </button>
              <button className="w-full px-4 py-2 flex items-center justify-between text-gray-500 hover:bg-[#f3f2ef] hover:text-black transition-colors">
                <div className="flex items-center gap-3">
                  <BookOpen className="h-5 w-5" />
                  <span className="text-sm font-semibold">Newsletters</span>
                </div>
              </button>
              <button className="w-full px-4 py-2 flex items-center justify-between text-gray-500 hover:bg-[#f3f2ef] hover:text-black transition-colors">
                <div className="flex items-center gap-3">
                  <Hash className="h-5 w-5" />
                  <span className="text-sm font-semibold">Hashtags</span>
                </div>
              </button>
            </div>
            <div className="border-t border-[#ebebeb] p-3 text-center">
              <button className="text-sm font-semibold text-gray-500 hover:text-black hover:bg-gray-100 px-3 py-1 rounded transition-colors w-full">
                Show less
              </button>
            </div>
          </div>
          
          <div className="rounded-lg bg-white border border-[#ebebeb] shadow-[0_1px_2px_rgba(0,0,0,0.08)] p-3 text-center cursor-pointer hover:shadow-md transition-shadow">
            <p className="text-xs text-gray-500 mb-2">Unlock your full potential with LinkedIn Premium</p>
            <div className="flex items-center justify-center gap-2 text-sm font-semibold text-black">
              <div className="h-3 w-3 bg-amber-500 rounded-sm" />
              See who's viewed your profile in the last 90 days
            </div>
            <button className="mt-3 border border-[#0a66c2] text-[#0a66c2] font-semibold text-sm rounded-full px-4 py-1.5 hover:bg-blue-50 transition-colors w-full">
              Try for free
            </button>
          </div>
          
          {/* Footer links */}
          <div className="px-6 py-4 text-xs text-gray-500 text-center leading-relaxed">
            <div className="flex flex-wrap justify-center gap-x-4 gap-y-2 mb-2">
              <a href="#" className="hover:text-[#0a66c2] hover:underline">About</a>
              <a href="#" className="hover:text-[#0a66c2] hover:underline">Accessibility</a>
              <a href="#" className="hover:text-[#0a66c2] hover:underline">Help Center</a>
              <a href="#" className="hover:text-[#0a66c2] hover:underline">Privacy & Terms</a>
              <a href="#" className="hover:text-[#0a66c2] hover:underline">Ad Choices</a>
            </div>
            <p>LinkedIn Corporation © 2026</p>
          </div>
        </div>

        {/* Right Main Area */}
        <div className="flex-1 space-y-4">
          
          {/* 1. Invitations (Agent Proposals) */}
          <div className="rounded-lg bg-white border border-[#ebebeb] shadow-[0_1px_2px_rgba(0,0,0,0.08)]">
            <div className="flex items-center justify-between px-4 py-3 border-b border-[#ebebeb]">
              <h2 className="text-base font-semibold text-black">Invitations</h2>
              <button className="text-sm font-semibold text-gray-500 hover:text-black transition-colors">
                Manage
              </button>
            </div>

            {proposals.length === 0 ? (
              <div className="p-4 text-sm text-gray-500 text-center">No pending invitations.</div>
            ) : (
              <div className="divide-y divide-[#ebebeb]">
                {proposals.map((prop) => (
                  <div key={prop.target_profile_id} className="p-4 flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                    <div className="flex gap-4">
                      <Avatar className="h-[72px] w-[72px] shrink-0">
                        <AvatarFallback className="bg-gray-200 text-gray-700 font-bold text-xl">
                          {prop.target_name.split(' ').map((n) => n[0]).join('')}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <h4 className="text-base font-semibold text-black hover:text-[#0a66c2] hover:underline cursor-pointer">
                          {prop.target_name}
                        </h4>
                        <p className="text-sm text-gray-600 line-clamp-1">{prop.target_headline}</p>
                        
                        <div className="mt-2 p-3 rounded bg-[#f3f2ef] border border-[#ebebeb] text-sm text-black">
                          <span className="font-semibold text-gray-600 mr-2 text-xs">Agent Note:</span>
                          {prop.proposed_note}
                        </div>
                        
                        <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
                          <span className="font-semibold">Match:</span>
                          <span className="px-2 py-0.5 rounded-full bg-green-100 text-green-700 font-bold border border-green-200">
                            {prop.match_score}%
                          </span>
                          <span className="font-semibold ml-2">Evidence:</span>
                          {prop.evidence_citations.map((cite, i) => (
                            <span key={i} className="text-[#0a66c2] hover:underline cursor-pointer">{cite}</span>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-start sm:self-center shrink-0">
                      <button
                        className="text-gray-500 font-semibold text-base px-4 py-1.5 hover:bg-gray-100 rounded-full transition-colors"
                        onClick={() => handleDismissProposal(prop.target_profile_id)}
                      >
                        Ignore
                      </button>
                      <button
                        className="border border-[#0a66c2] text-[#0a66c2] font-semibold text-base px-4 py-1.5 hover:bg-blue-50 hover:border-2 rounded-full transition-all"
                        onClick={() => handleApproveProposal(prop)}
                      >
                        Accept
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 2. People you may know */}
          <div className="rounded-lg bg-white border border-[#ebebeb] shadow-[0_1px_2px_rgba(0,0,0,0.08)]">
            <div className="flex items-center justify-between px-4 py-3">
              <h2 className="text-base font-semibold text-black">People you may know</h2>
              <button className="text-sm font-semibold text-gray-500 hover:text-black transition-colors">
                See all
              </button>
            </div>

            {/* Search/Filter embedded minimally for OS functionality */}
            <div className="px-4 pb-4">
               <div className="relative w-full">
                  <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-500" />
                  <input
                    type="text"
                    placeholder="Search people..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="h-9 w-full rounded bg-[#eef3f8] pl-9 pr-3 text-sm text-black placeholder:text-gray-600 focus:outline-none focus:ring-1 focus:ring-black/20"
                  />
                </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 px-4 pb-4">
              {filteredProfiles.map((p) => {
                const isSent = sentMap[p.id] || p.connection_status === 'PENDING';
                return (
                  <div key={p.id} className="rounded-lg border border-[#ebebeb] overflow-hidden flex flex-col hover:shadow-md transition-shadow h-full">
                    <div className="h-[60px] bg-[#a0b4b7] relative">
                      <button className="absolute top-2 right-2 h-7 w-7 rounded-full bg-black/40 hover:bg-black/60 flex items-center justify-center transition-colors">
                        <X className="h-4 w-4 text-white" />
                      </button>
                    </div>
                    
                    <div className="px-3 pb-3 flex flex-col flex-1 relative mt-[-36px] items-center text-center">
                      <Avatar className="h-[72px] w-[72px] border-2 border-white ring-2 ring-white mb-2 cursor-pointer">
                        <AvatarFallback className="bg-gray-200 text-gray-700 font-bold text-xl">
                          {p.full_name.split(' ').map((n) => n[0]).join('')}
                        </AvatarFallback>
                      </Avatar>
                      
                      <h4 className="text-base font-semibold text-black leading-tight hover:underline cursor-pointer line-clamp-1">
                        {p.full_name}
                      </h4>
                      <p className="text-xs text-gray-500 mt-1 line-clamp-2 min-h-[32px]">
                        {p.headline}
                      </p>
                      
                      <div className="text-[10px] text-gray-500 mt-2 flex items-center gap-1 justify-center">
                        <Users className="h-3 w-3" />
                        <span>Based on your profile</span>
                      </div>

                      <div className="mt-auto pt-4 w-full">
                        {isSent ? (
                          <button disabled className="w-full h-8 rounded-full border border-gray-400 text-gray-500 font-semibold text-sm flex items-center justify-center gap-1">
                            <Check className="h-4 w-4" />
                            Pending
                          </button>
                        ) : (
                          <button
                            className="w-full h-8 rounded-full border border-[#0a66c2] text-[#0a66c2] font-semibold text-sm flex items-center justify-center gap-1 hover:bg-[#eaf3fc] hover:border-[2px] transition-all"
                            onClick={() => handleDirectConnect(p)}
                          >
                            Connect
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
