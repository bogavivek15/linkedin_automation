import React, { useState } from 'react';
import {
  Home,
  Users,
  Briefcase,
  MessageSquare,
  Bell,
  Search,
  ChevronDown,
  User,
  Shield,
  Zap
} from 'lucide-react';
import { Avatar, AvatarFallback } from './ui/Avatar';
import { Badge } from './ui/Badge';
import { cn } from '../utils/cn';
import { getProfile } from '../services/api';

export function NetworkHeader({ currentTab, onSelectTab }) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [profile, setProfile] = useState(null);

  React.useEffect(() => {
    getProfile().then((data) => setProfile(data));
  }, []);

  const initials = profile?.full_name ? profile.full_name.split(' ').map(n => n[0]).join('') : 'U';
  const displayName = profile?.full_name || 'Your Name';
  const displayHeadline = profile?.headline || 'Member';

  const navItems = [
    { id: 'feed', label: 'Home', icon: Home },
    { id: 'network', label: 'My Network', icon: Users, badge: '2' },
    { id: 'jobs', label: 'Jobs', icon: Briefcase },
    { id: 'messages', label: 'Messaging', icon: MessageSquare, badge: '1' },
    {
      id: 'command-center',
      label: 'Command Center',
      icon: Zap,
      badge: '3',
      highlight: true,
    },
  ];

  return (
    <header className="sticky top-0 z-50 w-full bg-white border-b border-[#ebebeb] shadow-sm">
      <div className="max-w-[1128px] mx-auto px-4 h-[52px] flex items-center justify-between">
        
        {/* Left: Brand + Search */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => onSelectTab('feed')}
            className="flex items-center group focus:outline-none shrink-0"
          >
            <div className="h-[34px] w-[34px] rounded bg-[#0a66c2] flex items-center justify-center font-bold text-white text-xl">
              in
            </div>
          </button>

          {/* Search Box */}
          <div className="relative hidden md:flex items-center ml-2">
            <Search className="absolute left-3 h-4 w-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-[34px] w-[280px] rounded bg-[#eef3f8] pl-10 pr-4 text-sm text-black placeholder:text-gray-600 focus:outline-none focus:w-[360px] transition-all border border-transparent focus:border-black/20 focus:bg-white"
            />
          </div>
        </div>

          {/* Center/Right: Primary Nav Items */}
        <nav className="flex items-center h-full overflow-x-auto no-scrollbar">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            const isHighlight = item.highlight;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={cn(
                  "relative flex flex-col items-center justify-center h-full px-2 sm:px-5 min-w-[48px] sm:min-w-[80px] text-xs transition-colors border-b-2",
                  isActive
                    ? "border-black text-black"
                    : "border-transparent text-gray-500 hover:text-black",
                  isHighlight && !isActive && "bg-amber-50/50"
                )}
              >
                <div className="relative flex items-center justify-center h-6 w-6">
                  <Icon 
                    className={cn(
                      "h-6 w-6", 
                      isActive ? "text-black fill-current" : isHighlight ? "text-amber-500" : "text-gray-500",
                      isHighlight && "animate-pulse"
                    )} 
                    strokeWidth={isActive ? 2.5 : 2} 
                  />
                  {item.badge && (
                    <span className={cn(
                      "absolute -top-1 -right-2 px-1 min-w-[16px] h-4 flex items-center justify-center text-[10px] font-bold rounded-full text-white border-2 border-white",
                      isHighlight ? "bg-amber-500 animate-pulse" : "bg-[#cc1016]"
                    )}>
                      {item.badge}
                    </span>
                  )}
                </div>
                <span className={cn(
                  "hidden sm:block text-[12px] mt-0.5 whitespace-nowrap font-semibold", 
                  isActive ? "text-black" : isHighlight ? "text-amber-600" : ""
                )}>
                  {item.label}
                </span>
              </button>
            );
          })}

          {/* Profile & Contextual Intelligence Menu */}
          <div className="relative h-full flex items-center border-l border-[#ebebeb] pl-2 ml-2 shrink-0">
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex flex-col items-center justify-center h-full px-2 min-w-[48px] sm:min-w-[80px] text-gray-500 hover:text-black transition-colors focus:outline-none"
            >
              <Avatar className="h-6 w-6">
                <AvatarFallback className="bg-gray-200 text-gray-700 text-xs font-bold">{initials}</AvatarFallback>
              </Avatar>
              <div className="hidden sm:flex items-center gap-1 mt-0.5 text-[12px]">
                Me
                <ChevronDown className="h-3.5 w-3.5" />
              </div>
            </button>

            {/* Dropdown menu */}
            {dropdownOpen && (
              <div
                className="absolute top-12 right-0 w-[280px] rounded-bl-lg rounded-br-lg rounded-tl-lg border border-[#ebebeb] bg-white shadow-[0_4px_12px_rgba(0,0,0,0.15)] z-50 animate-fade-in"
                onMouseLeave={() => setDropdownOpen(false)}
              >
                <div className="px-4 py-3 flex gap-3 border-b border-[#ebebeb]">
                  <Avatar className="h-[56px] w-[56px] shrink-0">
                    <AvatarFallback className="bg-gray-200 text-gray-700 font-bold text-xl">{initials}</AvatarFallback>
                  </Avatar>
                  <div>
                    <h3 className="text-base font-semibold text-black leading-tight">{displayName}</h3>
                    <p className="text-sm text-gray-600 mt-1 line-clamp-2 leading-tight">{displayHeadline}</p>
                  </div>
                </div>

                <div className="px-4 py-2 border-b border-[#ebebeb]">
                  <button
                    onClick={() => {
                      onSelectTab('profile');
                      setDropdownOpen(false);
                    }}
                    className="w-full h-7 rounded-full border border-[#0a66c2] text-[#0a66c2] text-sm font-semibold hover:bg-[#eaf3fc] hover:border-[2px] transition-all"
                  >
                    View Profile
                  </button>
                </div>

                <div className="py-2">
                  <h4 className="px-4 py-1 text-sm font-semibold text-black">Account</h4>
                  <button
                    onClick={() => {
                      onSelectTab('command-center');
                      setDropdownOpen(false);
                    }}
                    className="w-full px-4 py-1.5 flex flex-col text-sm text-gray-600 hover:underline text-left"
                  >
                    <div className="flex items-center gap-2 font-semibold">
                      <Zap className="h-4 w-4 text-amber-500 fill-amber-500" /> Try Premium for $0
                    </div>
                  </button>
                  <button className="w-full px-4 py-1.5 text-sm text-gray-600 hover:underline text-left">
                    Settings & Privacy
                  </button>
                </div>
                
                <div className="py-2 border-t border-[#ebebeb]">
                  <button className="w-full px-4 py-1.5 text-sm text-gray-600 hover:underline text-left">
                    Sign Out
                  </button>
                </div>
              </div>
            )}
          </div>
        </nav>
      </div>
    </header>
  );
}

