import React, { useState, useEffect } from 'react';
import {
  ThumbsUp,
  MessageSquare,
  Repeat,
  Send,
  MoreHorizontal,
  Image as ImageIcon,
  CalendarDays,
  Newspaper,
  CheckCircle2,
  Bookmark,
  Zap,
  ArrowRight,
  Activity
} from 'lucide-react';
import { Avatar, AvatarFallback } from '../components/ui/Avatar';
import { Badge } from '../components/ui/Badge';
import { getFeed, likePost, getComments, postComment, getProfile } from '../services/api';

export function FeedPage({ onNavigate }) {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openPostId, setOpenPostId] = useState(null);
  const [comments, setComments] = useState({});
  const [commentInput, setCommentInput] = useState('');
  const [toastMessage, setToastMessage] = useState(null);
  const [showBanner, setShowBanner] = useState(true);
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    getFeed().then((data) => {
      setPosts(data || []);
      setLoading(false);
    });
    getProfile().then((data) => setProfile(data));
  }, []);

  async function handleLike(postId) {
    await likePost(postId);
    setPosts((prev) =>
      prev.map((p) =>
        p.id === postId
          ? {
              ...p,
              liked_by_user: !p.liked_by_user,
              likes_count: p.liked_by_user ? p.likes_count - 1 : p.likes_count + 1,
            }
          : p
      )
    );
  }

  async function handleToggleComments(postId) {
    if (openPostId === postId) {
      setOpenPostId(null);
      return;
    }
    setOpenPostId(postId);
    if (!comments[postId]) {
      const fetched = await getComments(postId);
      setComments((prev) => ({ ...prev, [postId]: fetched }));
    }
  }

  async function handleAddComment(postId, isAgentDrafted = false, agentText = '') {
    const text = isAgentDrafted ? agentText : commentInput;
    if (!text.trim()) return;

    const newComment = await postComment(
      postId,
      text,
      isAgentDrafted,
      isAgentDrafted ? 'Verified LangGraph state machine & pgvector memory hash' : null
    );

    setComments((prev) => ({
      ...prev,
      [postId]: [...(prev[postId] || []), newComment],
    }));

    setPosts((prev) =>
      prev.map((p) => (p.id === postId ? { ...p, comments_count: p.comments_count + 1 } : p))
    );

    if (!isAgentDrafted) setCommentInput('');
    setToastMessage(isAgentDrafted ? 'Agent draft approved and posted to feed!' : 'Comment published.');
    setTimeout(() => setToastMessage(null), 3000);
  }

  return (
    <div className="max-w-[1128px] mx-auto py-6 px-0 sm:px-4">
      {/* Toast Alert */}
      {toastMessage && (
        <div className="fixed bottom-6 left-6 z-50 bg-[#333333] text-white text-sm px-4 py-3 rounded shadow-lg flex items-center gap-2 animate-fade-in">
          <CheckCircle2 className="h-4 w-4 text-green-500" />
          {toastMessage}
        </div>
      )}

      {/* Agent Command Center Banner */}
      {showBanner && (
        <div className="mb-6 mx-4 sm:mx-0">
          <div className="bg-gradient-to-r from-amber-50 to-orange-50 border-2 border-amber-300 rounded-lg p-5 shadow-lg relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-amber-200 rounded-full blur-3xl opacity-30" />
            <button
              onClick={() => setShowBanner(false)}
              className="absolute top-3 right-3 text-gray-400 hover:text-gray-600 transition-colors"
            >
              ✕
            </button>
            <div className="relative z-10">
              <div className="flex items-center gap-3 mb-3">
                <div className="bg-amber-500 p-2 rounded-lg">
                  <Zap className="h-6 w-6 text-white fill-white animate-pulse" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                    Your Agents Are Working! 
                    <Activity className="h-5 w-5 text-green-600 animate-pulse" />
                  </h3>
                  <p className="text-sm text-gray-700 mt-0.5">
                    Click to see real-time agent activity, job discoveries, and pending approvals
                  </p>
                </div>
              </div>
              <button
                onClick={() => onNavigate('command-center')}
                className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white font-bold px-6 py-3 rounded-full transition-all transform hover:scale-105 shadow-lg flex items-center gap-2 mt-4"
              >
                <Zap className="h-5 w-5 fill-white" />
                Open Command Center
                <ArrowRight className="h-5 w-5" />
              </button>
              <p className="text-xs text-gray-600 mt-3 flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                Orchestrator running • Trust Agent active • Jobs being discovered
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="flex flex-col lg:flex-row gap-6">
        
        {/* Left Column: Candidate Identity (225px) */}
        <div className="hidden lg:block w-[225px] shrink-0 space-y-2">
          <div className="rounded-lg bg-white border border-[#ebebeb] overflow-hidden shadow-[0_1px_2px_rgba(0,0,0,0.08)]">
            <div className="h-14 bg-[#a0b4b7]" />
            <div className="px-3 pb-3 text-center relative mt-[-28px]">
              <div 
                className="inline-block cursor-pointer"
                onClick={() => onNavigate('profile')}
              >
                <Avatar className="h-[72px] w-[72px] mx-auto border-2 border-white ring-2 ring-white">
                  <AvatarFallback className="bg-gray-200 text-gray-700 font-bold text-2xl">
                    {profile?.full_name ? profile.full_name.split(' ').map(n => n[0]).join('') : 'U'}
                  </AvatarFallback>
                </Avatar>
              </div>
              <h3 
                className="mt-4 text-base font-semibold text-black hover:underline cursor-pointer leading-tight"
                onClick={() => onNavigate('profile')}
              >
                {profile?.full_name || 'Your Name'}
              </h3>
              <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                {profile?.headline || 'Upload your resume to get started'}
              </p>
            </div>
            
            <div className="border-t border-[#ebebeb] py-3">
              <div className="px-3 py-1 flex items-center justify-between text-xs hover:bg-[#f3f2ef] cursor-pointer transition-colors">
                <span className="text-gray-500 font-semibold">Connections</span>
                <span className="text-[#0a66c2] font-semibold">500+</span>
              </div>
              <div className="px-3 py-1 flex items-center justify-between text-xs hover:bg-[#f3f2ef] cursor-pointer transition-colors">
                <span className="text-gray-500 font-semibold">Profile viewers</span>
                <span className="text-[#0a66c2] font-semibold">47</span>
              </div>
            </div>

            <div className="border-t border-[#ebebeb] px-3 py-3 hover:bg-[#f3f2ef] cursor-pointer transition-colors">
              <p className="text-xs text-gray-500">Access exclusive tools & insights</p>
              <div className="flex items-center gap-1.5 mt-0.5 text-xs font-semibold text-black">
                <div className="h-3 w-3 rounded-sm bg-amber-500" />
                Try Premium for $0
              </div>
            </div>

            <div className="border-t border-[#ebebeb] px-3 py-3 hover:bg-[#f3f2ef] cursor-pointer transition-colors flex items-center gap-2 text-xs font-semibold text-gray-600">
              <Bookmark className="h-4 w-4 text-gray-500 fill-gray-500" />
              My items
            </div>
          </div>
        </div>

        {/* Center Column: Professional Feed (540px) */}
        <div className="flex-1 lg:max-w-[540px] space-y-2">
          
          {/* Post Creation Box */}
          <div className="rounded-lg bg-white border border-[#ebebeb] shadow-[0_1px_2px_rgba(0,0,0,0.08)] p-3">
            <div className="flex gap-2">
              <Avatar className="h-12 w-12 shrink-0">
                <AvatarFallback className="bg-gray-200 text-gray-700 font-bold">
                  {profile?.full_name ? profile.full_name.split(' ').map(n => n[0]).join('') : 'U'}
                </AvatarFallback>
              </Avatar>
              <button className="flex-1 rounded-full border border-gray-400 bg-white text-left px-4 text-sm text-gray-500 font-semibold hover:bg-gray-100 transition-colors h-12">
                Start a post
              </button>
            </div>
            <div className="flex items-center justify-between mt-2 px-2">
              <button className="flex items-center gap-2 p-2 rounded hover:bg-gray-100 transition-colors text-sm text-gray-600 font-semibold">
                <ImageIcon className="h-5 w-5 text-[#378fe9]" />
                Media
              </button>
              <button className="flex items-center gap-2 p-2 rounded hover:bg-gray-100 transition-colors text-sm text-gray-600 font-semibold">
                <CalendarDays className="h-5 w-5 text-[#c37d16]" />
                Event
              </button>
              <button className="flex items-center gap-2 p-2 rounded hover:bg-gray-100 transition-colors text-sm text-gray-600 font-semibold">
                <Newspaper className="h-5 w-5 text-[#e16745]" />
                Write article
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between px-1 text-xs">
            <hr className="flex-1 border-[#ebebeb]" />
            <span className="px-2 text-gray-500">
              Sort by: <strong className="text-black">Top</strong>
            </span>
          </div>

          {/* Feed Posts */}
          {posts.map((post) => (
            <div key={post.id} className="rounded-lg bg-white border border-[#ebebeb] shadow-[0_1px_2px_rgba(0,0,0,0.08)]">
              {/* Agent Relevance Observation Card (Repurposed as suggested action) */}
              {post.agent_relevance_note && (
                <div className="border-b border-[#ebebeb] px-4 py-2 flex items-start justify-between bg-gray-50/50">
                  <div className="flex items-center gap-2 text-xs font-semibold text-gray-600">
                    <Avatar className="h-6 w-6">
                      <AvatarFallback className="bg-amber-100 text-amber-700 text-[10px]">AI</AvatarFallback>
                    </Avatar>
                    CareerOS Agent Observation
                  </div>
                  <button 
                    onClick={() => handleAddComment(
                      post.id,
                      true,
                      `Insightful point! In CareerOS, we tackled this exact problem using deterministic verification gates before LLM submission. Citing verifiable claim hashes ensures zero hallucinations.`
                    )}
                    className="text-xs text-[#0a66c2] font-semibold hover:bg-blue-50 px-2 py-1 rounded transition-colors"
                  >
                    Draft Comment
                  </button>
                </div>
              )}

              <div className="p-4 space-y-3">
                {/* Author Metadata */}
                <div className="flex items-start justify-between">
                  <div className="flex gap-2">
                    <Avatar className="h-12 w-12">
                      <AvatarFallback className="bg-gray-200 text-gray-700 font-bold">
                        {post.author_name.split(' ').map(n => n[0]).join('')}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex flex-col">
                      <div className="flex items-center gap-1">
                        <span className="text-sm font-semibold text-black hover:text-[#0a66c2] hover:underline cursor-pointer">
                          {post.author_name}
                        </span>
                        <span className="text-sm text-gray-500">• 1st</span>
                      </div>
                      <span className="text-xs text-gray-500 line-clamp-1">{post.author_headline}</span>
                      <span className="text-xs text-gray-500">2h • Edited • 🌐</span>
                    </div>
                  </div>
                  <button className="text-gray-500 hover:bg-gray-100 p-1.5 rounded-full transition-colors">
                    <MoreHorizontal className="h-5 w-5" />
                  </button>
                </div>

                {/* Post Content */}
                <div className="text-sm text-black leading-relaxed whitespace-pre-line">
                  {post.content}
                </div>

                {/* Tags */}
                {post.tags && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {post.tags.map((tag) => (
                      <span key={tag} className="text-sm text-[#0a66c2] hover:underline cursor-pointer font-semibold">
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Social Counts */}
              <div className="px-4 py-2 flex items-center justify-between text-xs text-gray-500 border-b border-[#ebebeb]">
                <div className="flex items-center gap-1">
                  <div className="h-4 w-4 rounded-full bg-blue-100 flex items-center justify-center">
                    <ThumbsUp className="h-2.5 w-2.5 text-[#0a66c2]" />
                  </div>
                  <span>{post.likes_count}</span>
                </div>
                <div className="hover:text-[#0a66c2] hover:underline cursor-pointer">
                  {post.comments_count} comments
                </div>
              </div>

              {/* Action Bar */}
              <div className="px-2 py-1 flex items-center justify-between">
                <button
                  onClick={() => handleLike(post.id)}
                  className={`flex items-center justify-center gap-1.5 flex-1 p-3 rounded hover:bg-gray-100 transition-colors text-sm font-semibold ${
                    post.liked_by_user ? 'text-[#0a66c2]' : 'text-gray-600'
                  }`}
                >
                  <ThumbsUp className={post.liked_by_user ? "h-5 w-5 fill-current" : "h-5 w-5"} />
                  Like
                </button>
                <button
                  onClick={() => handleToggleComments(post.id)}
                  className="flex items-center justify-center gap-1.5 flex-1 p-3 rounded hover:bg-gray-100 transition-colors text-sm font-semibold text-gray-600"
                >
                  <MessageSquare className="h-5 w-5" />
                  Comment
                </button>
                <button className="flex items-center justify-center gap-1.5 flex-1 p-3 rounded hover:bg-gray-100 transition-colors text-sm font-semibold text-gray-600">
                  <Repeat className="h-5 w-5" />
                  Repost
                </button>
                <button className="flex items-center justify-center gap-1.5 flex-1 p-3 rounded hover:bg-gray-100 transition-colors text-sm font-semibold text-gray-600">
                  <Send className="h-5 w-5" />
                  Send
                </button>
              </div>

              {/* Comment Section */}
              {openPostId === post.id && (
                <div className="px-4 pb-4 pt-2">
                  <div className="flex gap-2">
                    <Avatar className="h-10 w-10 shrink-0">
                      <AvatarFallback className="bg-gray-200 text-gray-700 font-bold">VB</AvatarFallback>
                    </Avatar>
                    <div className="flex-1 flex flex-col gap-2">
                      <div className="rounded-full border border-gray-400 bg-white flex items-center px-4 min-h-[40px] focus-within:border-gray-600 focus-within:border-2 transition-all">
                        <input
                          type="text"
                          placeholder="Add a comment..."
                          value={commentInput}
                          onChange={(e) => setCommentInput(e.target.value)}
                          onKeyDown={(e) => e.key === 'Enter' && handleAddComment(post.id)}
                          className="flex-1 bg-transparent border-none focus:outline-none text-sm text-black placeholder:text-gray-500 py-2"
                        />
                      </div>
                      {commentInput.trim() && (
                        <div className="flex justify-start">
                          <button 
                            onClick={() => handleAddComment(post.id)}
                            className="bg-[#0a66c2] text-white rounded-full px-4 py-1 text-sm font-semibold hover:bg-[#004182] transition-colors"
                          >
                            Post
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Render existing comments */}
                  <div className="mt-4 space-y-3">
                    {(comments[post.id] || []).map((c) => (
                      <div key={c.id} className="flex gap-2">
                        <Avatar className="h-10 w-10 shrink-0">
                          <AvatarFallback className="bg-gray-200 text-gray-700 font-bold text-xs">
                            {c.author_name.split(' ').map(n => n[0]).join('')}
                          </AvatarFallback>
                        </Avatar>
                        <div className="flex-1">
                          <div className="bg-[#f2f2f2] rounded-bl-lg rounded-br-lg rounded-tr-lg p-3 relative">
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-semibold text-black text-sm hover:text-[#0a66c2] hover:underline cursor-pointer">
                                {c.author_name}
                              </span>
                              <span className="text-xs text-gray-500">1h</span>
                            </div>
                            <p className="text-sm text-black">{c.content}</p>
                            
                            {c.agent_drafted && (
                              <div className="mt-2 pt-2 border-t border-gray-300 text-[10px] text-gray-500 flex items-center gap-1">
                                <CheckCircle2 className="h-3 w-3 text-green-600" />
                                Agent Grounded: {c.evidence_citation}
                              </div>
                            )}
                          </div>
                          <div className="flex items-center gap-3 mt-1 ml-2 text-xs font-semibold text-gray-500">
                            <button className="hover:bg-gray-200 px-1 rounded transition-colors">Like</button>
                            <span className="w-[1px] h-3 bg-gray-400" />
                            <button className="hover:bg-gray-200 px-1 rounded transition-colors">Reply</button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Right Column: News / Recommended Widgets (315px) */}
        <div className="hidden lg:block w-[315px] shrink-0 space-y-2">
          <div className="rounded-lg bg-white border border-[#ebebeb] shadow-[0_1px_2px_rgba(0,0,0,0.08)] p-4">
            <h2 className="text-base font-semibold text-black mb-3">LinkedIn News</h2>
            <div className="space-y-4">
              <div className="cursor-pointer group">
                <div className="flex items-start gap-2">
                  <div className="mt-1.5 h-1.5 w-1.5 rounded-full bg-gray-400 shrink-0" />
                  <div>
                    <h3 className="text-sm font-semibold text-black group-hover:text-[#0a66c2] group-hover:underline leading-snug">
                      AI hiring surges in tech
                    </h3>
                    <p className="text-xs text-gray-500 mt-0.5">Top news • 10,243 readers</p>
                  </div>
                </div>
              </div>
              <div className="cursor-pointer group">
                <div className="flex items-start gap-2">
                  <div className="mt-1.5 h-1.5 w-1.5 rounded-full bg-gray-400 shrink-0" />
                  <div>
                    <h3 className="text-sm font-semibold text-black group-hover:text-[#0a66c2] group-hover:underline leading-snug">
                      Remote work policies shift
                    </h3>
                    <p className="text-xs text-gray-500 mt-0.5">1d ago • 5,432 readers</p>
                  </div>
                </div>
              </div>
              <div className="cursor-pointer group">
                <div className="flex items-start gap-2">
                  <div className="mt-1.5 h-1.5 w-1.5 rounded-full bg-gray-400 shrink-0" />
                  <div>
                    <h3 className="text-sm font-semibold text-black group-hover:text-[#0a66c2] group-hover:underline leading-snug">
                      CareerOS automates outreach
                    </h3>
                    <p className="text-xs text-gray-500 mt-0.5">12h ago • 3,998 readers</p>
                  </div>
                </div>
              </div>
            </div>
            <button className="mt-3 text-sm font-semibold text-gray-500 hover:bg-gray-100 px-2 py-1 rounded transition-colors flex items-center gap-1">
              Show more <span className="text-lg leading-none mt-[-4px]">⌄</span>
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

      </div>
    </div>
  );
}

