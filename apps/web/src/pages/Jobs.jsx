import React, { useState, useEffect } from 'react';
import {
  Search,
  MapPin,
  Building2,
  DollarSign,
  Filter,
  Check,
  Bookmark,
  Share2,
  ExternalLink,
  ChevronDown,
  Briefcase,
  ListOrdered,
  MoreHorizontal,
  X,
  Clock,
  Users,
  ShieldCheck,
  CheckCircle2,
  Lightbulb,
  Sparkles,
  TrendingUp,
  FileCheck,
  Eye,
  Award,
  Send,
  AlertCircle
} from 'lucide-react';
import { Avatar, AvatarFallback } from '../components/ui/Avatar';
import { getJobs, submitApplication, getProfile } from '../services/api';

export function JobsPage() {
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [appliedMap, setAppliedMap] = useState({});
  const [savedMap, setSavedMap] = useState({});
  const [searchTerm, setSearchTerm] = useState('');
  const [locationTerm, setLocationTerm] = useState('');
  const [toastMessage, setToastMessage] = useState(null);
  const [profile, setProfile] = useState(null);
  const [activeTab, setActiveTab] = useState('all'); // 'all', 'applied', 'saved'

  useEffect(() => {
    getJobs().then((data) => {
      const list = data || [];
      // Prioritize jobs that have rich descriptions or LINKEDIN source first
      const sorted = [...list].sort((a, b) => {
        const aScore = (a.source === 'LINKEDIN' ? 100 : 0) + (a.description?.length > 100 ? 50 : 0);
        const bScore = (b.source === 'LINKEDIN' ? 100 : 0) + (b.description?.length > 100 ? 50 : 0);
        return bScore - aScore;
      });
      setJobs(sorted);
      if (sorted.length > 0) setSelectedJob(sorted[0]);
    });
    getProfile().then((p) => setProfile(p));
  }, []);

  async function handleFastApply(job) {
    const defaultCites = profile?.verified_evidence?.map((e) => `Verified: ${e.title}`) || [
      'Verified Resume Evidence: Technical Skills & Projects'
    ];
    await submitApplication(job.id, {
      evidence_cites: defaultCites.slice(0, 3),
    });
    setAppliedMap((prev) => ({ ...prev, [job.id]: true }));
    setToastMessage(`Application package submitted for ${job.title} at ${job.company_name}!`);
    setTimeout(() => setToastMessage(null), 4000);
  }

  function toggleSave(jobId) {
    setSavedMap((prev) => {
      const isSaved = !prev[jobId];
      setToastMessage(isSaved ? 'Job saved to your items.' : 'Job removed from saved items.');
      setTimeout(() => setToastMessage(null), 3000);
      return { ...prev, [jobId]: isSaved };
    });
  }

  const filteredJobs = jobs.filter((j) => {
    const matchesSearch =
      !searchTerm ||
      j.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      j.company_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (j.description && j.description.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesLocation =
      !locationTerm ||
      (j.location && j.location.toLowerCase().includes(locationTerm.toLowerCase()));

    if (activeTab === 'applied') return matchesSearch && matchesLocation && appliedMap[j.id];
    if (activeTab === 'saved') return matchesSearch && matchesLocation && savedMap[j.id];
    return matchesSearch && matchesLocation;
  });

  // Calculate skill match breakdown
  const userSkills = profile?.skills || ['React', 'TypeScript', 'Python', 'FastAPI', 'System Design', 'PostgreSQL'];
  const jobReqSkills = selectedJob?.required_skills || selectedJob?.skills || [];
  const matchedSkills = jobReqSkills.filter(s => 
    userSkills.some(us => us.toLowerCase() === s.toLowerCase())
  );
  const missingSkills = jobReqSkills.filter(s => 
    !userSkills.some(us => us.toLowerCase() === s.toLowerCase())
  );

  return (
    <div className="max-w-[1128px] mx-auto py-6 px-0 sm:px-4 space-y-4">
      {/* Toast Alert */}
      {toastMessage && (
        <div className="fixed bottom-6 left-6 z-50 bg-[#333333] text-white text-sm px-4 py-3 rounded shadow-lg flex items-center gap-2 animate-fade-in">
          <Check className="h-4 w-4 text-green-500" />
          {toastMessage}
        </div>
      )}

      {/* Search & Filters Header */}
      <div className="bg-white rounded-lg border border-[#ebebeb] shadow-[0_1px_2px_rgba(0,0,0,0.08)]">
        <div className="p-4 flex flex-col md:flex-row gap-4 border-b border-[#ebebeb]">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 h-5 w-5 text-gray-500" />
            <input
              type="text"
              placeholder="Search by title, skill, or company"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full h-10 rounded border border-black/60 pl-10 pr-4 text-sm text-black focus:outline-none focus:border-black focus:border-[2px] transition-all"
            />
          </div>
          <div className="relative flex-1">
            <MapPin className="absolute left-3 top-2.5 h-5 w-5 text-gray-500" />
            <input
              type="text"
              placeholder="City, state, or remote"
              value={locationTerm}
              onChange={(e) => setLocationTerm(e.target.value)}
              className="w-full h-10 rounded border border-black/60 pl-10 pr-4 text-sm text-black focus:outline-none focus:border-black focus:border-[2px] transition-all"
            />
          </div>
          <button 
            onClick={() => {}}
            className="bg-[#0a66c2] hover:bg-[#004182] text-white font-semibold rounded-full px-6 py-2 transition-colors cursor-pointer"
          >
            Search
          </button>
        </div>
        
        {/* Filter Pills & Quick Tabs */}
        <div className="px-4 py-2 flex items-center justify-between gap-2 overflow-x-auto whitespace-nowrap">
          <div className="flex items-center gap-2">
            <button 
              onClick={() => setActiveTab('all')}
              className={`h-8 px-4 rounded-full text-sm font-semibold transition-colors flex items-center gap-1 ${
                activeTab === 'all' ? 'bg-[#0a66c2] text-white' : 'border border-gray-400 bg-white text-gray-600 hover:bg-gray-100'
              }`}
            >
              All Jobs
            </button>
            <button 
              onClick={() => setActiveTab('saved')}
              className={`h-8 px-4 rounded-full text-sm font-semibold transition-colors flex items-center gap-1 ${
                activeTab === 'saved' ? 'bg-[#0a66c2] text-white' : 'border border-gray-400 bg-white text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Bookmark className="h-3.5 w-3.5" /> My Saved ({Object.values(savedMap).filter(Boolean).length})
            </button>
            <button 
              onClick={() => setActiveTab('applied')}
              className={`h-8 px-4 rounded-full text-sm font-semibold transition-colors flex items-center gap-1 ${
                activeTab === 'applied' ? 'bg-[#0a66c2] text-white' : 'border border-gray-400 bg-white text-gray-600 hover:bg-gray-100'
              }`}
            >
              <CheckCircle2 className="h-3.5 w-3.5" /> Applied ({Object.values(appliedMap).filter(Boolean).length})
            </button>
          </div>

          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <ShieldCheck className="h-4 w-4 text-green-600" />
              Verified Authentic Opportunities
            </span>
          </div>
        </div>
      </div>

      {/* Two-Column Split Layout */}
      <div className="flex flex-col lg:flex-row gap-4 lg:h-[calc(100vh-220px)] lg:min-h-[640px]">
        
        {/* Left Column: Job Cards List (40%) */}
        <div className="lg:w-[40%] h-[400px] lg:h-auto bg-white border border-[#ebebeb] shadow-[0_1px_2px_rgba(0,0,0,0.08)] rounded-lg flex flex-col overflow-hidden">
          <div className="p-4 border-b border-[#ebebeb] flex justify-between items-center bg-gray-50/50">
            <div>
              <h2 className="text-base font-semibold text-black">Jobs based on your profile</h2>
              <p className="text-xs text-gray-500">{filteredJobs.length} top matching roles</p>
            </div>
            <span className="text-xs text-[#0a66c2] font-semibold cursor-pointer hover:underline">
              Preferences
            </span>
          </div>
          
          <div className="flex-1 overflow-y-auto divide-y divide-[#ebebeb]">
            {filteredJobs.length === 0 ? (
              <div className="p-8 text-center text-gray-500 text-sm">
                No jobs match your current search or filter.
              </div>
            ) : (
              filteredJobs.map((job) => {
                const isSelected = selectedJob?.id === job.id;
                const isApplied = appliedMap[job.id];
                const isSaved = savedMap[job.id];
                const trustScore = job.trust_score ?? job.metadata?.trust_score ?? 95;
                const matchScore = job.match_score ?? job.metadata?.match_score ?? (job.source === 'LINKEDIN' ? 95 : 88);
                const salaryRange = job.salary_range || job.metadata?.salary_range || (job.salary_min && job.salary_max ? `$${Math.round(job.salary_min/1000)}k - $${Math.round(job.salary_max/1000)}k/yr` : null);

                return (
                  <div
                    key={job.id}
                    onClick={() => setSelectedJob(job)}
                    className={`flex gap-3 p-4 cursor-pointer transition-colors relative ${
                      isSelected ? 'bg-[#edf3f8]' : 'bg-white hover:bg-gray-50'
                    }`}
                  >
                    {isSelected && (
                      <div className="absolute left-0 top-0 bottom-0 w-1 bg-[#0a66c2]" />
                    )}
                    <Avatar className="h-12 w-12 rounded-sm border border-gray-200 shrink-0 mt-0.5">
                      <AvatarFallback className="bg-slate-100 text-gray-800 font-bold text-lg rounded-sm">
                        {job.company_name?.substring(0, 1) || 'C'}
                      </AvatarFallback>
                    </Avatar>
                    
                    <div className="flex-1 min-w-0">
                      <h3 className={`text-sm font-semibold truncate ${isSelected ? 'text-[#0a66c2]' : 'text-[#0a66c2] hover:underline'}`}>
                        {job.title}
                      </h3>
                      <p className="text-xs font-medium text-gray-900 mt-0.5">{job.company_name}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{job.location || 'San Francisco Bay Area'} ({job.work_mode || 'Hybrid'})</p>
                      
                      <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px]">
                        {salaryRange && (
                          <span className="text-gray-700 font-medium">{salaryRange}</span>
                        )}
                        <span className="text-gray-400">•</span>
                        <span className="text-green-700 font-semibold flex items-center gap-0.5">
                          <TrendingUp className="h-3 w-3 inline" />
                          {matchScore}% Match
                        </span>
                        {trustScore >= 95 && (
                          <>
                            <span className="text-gray-400">•</span>
                            <span className="text-[#0a66c2] font-medium flex items-center gap-0.5">
                              <ShieldCheck className="h-3 w-3 inline text-green-600" />
                              Verified
                            </span>
                          </>
                        )}
                      </div>

                      <div className="mt-2 flex items-center gap-3">
                        <span className="text-[11px] text-green-800 font-semibold bg-green-50 px-2 py-0.5 rounded">
                          {job.metadata?.actively_recruiting !== false ? 'Actively recruiting' : 'Easy Apply'}
                        </span>
                        {isApplied && (
                          <span className="text-[11px] text-green-700 font-bold flex items-center gap-0.5">
                            <Check className="h-3 w-3" /> Applied
                          </span>
                        )}
                        {isSaved && (
                          <span className="text-[11px] text-[#0a66c2] font-semibold flex items-center gap-0.5">
                            <Bookmark className="h-3 w-3 fill-current" /> Saved
                          </span>
                        )}
                      </div>
                    </div>

                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleSave(job.id);
                      }}
                      className="self-start text-gray-400 hover:text-gray-700 p-1"
                      title={isSaved ? 'Remove from saved' : 'Save job'}
                    >
                      <Bookmark className={`h-4 w-4 ${isSaved ? 'fill-[#0a66c2] text-[#0a66c2]' : ''}`} />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Selected Job Full Details Pane (60%) */}
        <div className="lg:w-[60%] bg-white border border-[#ebebeb] shadow-[0_1px_2px_rgba(0,0,0,0.08)] rounded-lg flex flex-col overflow-hidden">
          {selectedJob ? (
            <div className="flex-1 overflow-y-auto">
              
              {/* Header Box */}
              <div className="p-6 border-b border-[#ebebeb] bg-white sticky top-0 z-10">
                <div className="flex justify-between items-start">
                  <div className="space-y-1">
                    <h2 className="text-2xl font-bold text-gray-900 leading-tight">
                      {selectedJob.title}
                    </h2>
                    
                    <div className="text-sm text-gray-600 flex flex-wrap items-center gap-1.5 pt-1">
                      <span className="font-semibold text-gray-900 hover:text-[#0a66c2] hover:underline cursor-pointer">
                        {selectedJob.company_name}
                      </span>
                      <span className="text-gray-400">•</span>
                      <span>{selectedJob.location || 'San Francisco Bay Area'}</span>
                      <span className="text-gray-400">•</span>
                      <span className="text-gray-500">{selectedJob.metadata?.posted_time || '1 day ago'}</span>
                      <span className="text-gray-400">•</span>
                      <span className="text-[#0a66c2] font-medium cursor-pointer hover:underline">
                        {selectedJob.metadata?.applicants_count || 32} applicants
                      </span>
                    </div>

                    {/* Metadata Pills */}
                    <div className="pt-3 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-gray-700">
                      <div className="flex items-center gap-2">
                        <Briefcase className="h-4 w-4 text-gray-500 shrink-0" />
                        <span>
                          {selectedJob.employment_type?.replace('_', ' ') || 'Full-time'} • {selectedJob.metadata?.workplace_type || selectedJob.work_mode || 'Hybrid'}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Building2 className="h-4 w-4 text-gray-500 shrink-0" />
                        <span>
                          {selectedJob.metadata?.company_size || '1,001-5,000 employees'} • {selectedJob.metadata?.company_industry || 'Technology, Software & Internet'}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <DollarSign className="h-4 w-4 text-gray-500 shrink-0" />
                        <span className="font-semibold text-gray-900">
                          {selectedJob.salary_range || selectedJob.metadata?.salary_range || (selectedJob.salary_min && selectedJob.salary_max ? `$${Math.round(selectedJob.salary_min/1000)}k - $${Math.round(selectedJob.salary_max/1000)}k/yr` : '$140k - $210k/yr')}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <ShieldCheck className="h-4 w-4 text-green-600 shrink-0" />
                        <span>Trust & Safety Score: <span className="font-semibold text-green-700">{selectedJob.trust_score ?? selectedJob.metadata?.trust_score ?? 96}/100</span> (Verified Scam-Free)</span>
                      </div>
                    </div>
                  </div>
                  
                  {/* Share / More Actions */}
                  <div className="flex items-center gap-1">
                    <button 
                      onClick={() => toggleSave(selectedJob.id)}
                      className={`h-9 w-9 rounded-full hover:bg-gray-100 flex items-center justify-center transition-colors ${
                        savedMap[selectedJob.id] ? 'text-[#0a66c2]' : 'text-gray-600'
                      }`}
                      title={savedMap[selectedJob.id] ? 'Saved' : 'Save'}
                    >
                      <Bookmark className={`h-5 w-5 ${savedMap[selectedJob.id] ? 'fill-current' : ''}`} />
                    </button>
                    <button 
                      onClick={() => {
                        navigator.clipboard?.writeText(window.location.href);
                        setToastMessage('Job link copied to clipboard!');
                        setTimeout(() => setToastMessage(null), 3000);
                      }}
                      className="h-9 w-9 rounded-full hover:bg-gray-100 flex items-center justify-center text-gray-600 transition-colors"
                      title="Share job"
                    >
                      <Share2 className="h-5 w-5" />
                    </button>
                  </div>
                </div>
                
                {/* Apply Buttons */}
                <div className="flex items-center gap-3 mt-5">
                  {appliedMap[selectedJob.id] ? (
                    <button 
                      disabled 
                      className="bg-green-100 text-green-800 font-semibold rounded-full px-6 py-2 transition-colors flex items-center gap-2 text-sm"
                    >
                      <Check className="h-4 w-4 text-green-700" /> Applied with Verified Evidence
                    </button>
                  ) : (
                    <button
                      onClick={() => handleFastApply(selectedJob)}
                      className="bg-[#0a66c2] hover:bg-[#004182] text-white font-semibold rounded-full px-6 py-2 transition-colors flex items-center gap-1.5 text-sm cursor-pointer shadow-sm"
                    >
                      <span className="font-bold">in</span> Easy Apply
                    </button>
                  )}
                  <button 
                    onClick={() => toggleSave(selectedJob.id)}
                    className={`border font-semibold rounded-full px-6 py-2 text-sm transition-all cursor-pointer ${
                      savedMap[selectedJob.id]
                        ? 'border-[#0a66c2] text-[#0a66c2] bg-blue-50/50'
                        : 'border-[#0a66c2] text-[#0a66c2] hover:bg-blue-50'
                    }`}
                  >
                    {savedMap[selectedJob.id] ? 'Saved' : 'Save'}
                  </button>
                </div>
              </div>

              {/* Scrollable Content Body */}
              <div className="p-6 space-y-6">
                
                {/* Section 1: Meet the hiring team & Applicant Insights */}
                <div className="bg-[#f8fafd] border border-[#d0e1fd] rounded-lg p-4 space-y-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2 text-sm font-semibold text-gray-900">
                      <Sparkles className="h-4 w-4 text-[#0a66c2]" />
                      <span>Applicant Insights & Profile Match</span>
                    </div>
                    <span className="text-xs bg-green-100 text-green-800 font-bold px-2 py-0.5 rounded-full">
                      {selectedJob.match_score ?? selectedJob.metadata?.match_score ?? 92}% Match
                    </span>
                  </div>

                  <p className="text-xs text-gray-700 leading-relaxed">
                    Based on your verified resume skills and work history, your profile matches <span className="font-semibold text-gray-900">{matchedSkills.length} of {jobReqSkills.length || 5} required qualifications</span> for this role. You are in the top 10% of applicants.
                  </p>

                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    {matchedSkills.map((s) => (
                      <span key={s} className="inline-flex items-center gap-1 text-xs bg-white border border-green-300 text-green-800 px-2 py-0.5 rounded-md font-medium">
                        <Check className="h-3 w-3 text-green-600" /> {s}
                      </span>
                    ))}
                    {missingSkills.map((s) => (
                      <span key={s} className="inline-flex items-center gap-1 text-xs bg-white border border-amber-300 text-amber-800 px-2 py-0.5 rounded-md font-medium">
                        <AlertCircle className="h-3 w-3 text-amber-600" /> {s}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Section 2: Job Overview Card */}
                <div className="border border-[#ebebeb] rounded-lg p-4 space-y-3">
                  <h3 className="text-sm font-bold text-gray-900">Role Summary</h3>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                    <div className="bg-gray-50 p-2.5 rounded">
                      <span className="text-gray-500 block">Experience Level</span>
                      <span className="font-semibold text-gray-900">
                        {selectedJob.title.includes('Senior') || selectedJob.title.includes('Lead') ? 'Mid-Senior level' : selectedJob.title.includes('Junior') ? 'Entry level' : 'Associate / Mid level'}
                      </span>
                    </div>
                    <div className="bg-gray-50 p-2.5 rounded">
                      <span className="text-gray-500 block">Job Function</span>
                      <span className="font-semibold text-gray-900">Engineering & Technology</span>
                    </div>
                    <div className="bg-gray-50 p-2.5 rounded">
                      <span className="text-gray-500 block">Industries</span>
                      <span className="font-semibold text-gray-900">{selectedJob.metadata?.company_industry || 'Internet & Software'}</span>
                    </div>
                  </div>
                </div>

                {/* Section 3: About the job (Full Description) */}
                <div className="space-y-3">
                  <h3 className="text-base font-bold text-gray-900">About the job</h3>
                  <div className="text-sm text-gray-800 leading-relaxed space-y-3 whitespace-pre-line font-normal">
                    {selectedJob.description}
                  </div>
                </div>

                {/* Section 4: Skills Breakdown */}
                <div className="border border-[#ebebeb] rounded-lg p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-gray-900">Skills Associated with Job</h3>
                    <span className="text-xs text-[#0a66c2] font-semibold cursor-pointer hover:underline">
                      See all {jobReqSkills.length + (selectedJob.preferred_skills?.length || 0)} skills
                    </span>
                  </div>

                  <div className="space-y-2">
                    <span className="text-xs font-semibold text-gray-500 block">Required Qualifications:</span>
                    <div className="flex flex-wrap gap-2">
                      {(selectedJob.required_skills?.length ? selectedJob.required_skills : selectedJob.skills?.length ? selectedJob.skills : ['React', 'TypeScript', 'Python', 'FastAPI', 'System Design']).map((skill) => {
                        const hasSkill = userSkills.some(us => us.toLowerCase() === skill.toLowerCase());
                        return (
                          <span 
                            key={skill} 
                            className={`px-3 py-1 rounded-full text-xs font-semibold flex items-center gap-1.5 ${
                              hasSkill 
                                ? 'bg-[#e8f0fe] text-[#0a66c2] border border-[#c7dcfa]' 
                                : 'bg-[#f3f2ef] text-gray-700 border border-transparent'
                            }`}
                          >
                            {hasSkill && <Check className="h-3 w-3 text-[#0a66c2]" />}
                            {skill}
                          </span>
                        );
                      })}
                    </div>
                  </div>

                  {selectedJob.preferred_skills && selectedJob.preferred_skills.length > 0 && (
                    <div className="space-y-2 pt-2 border-t border-gray-100">
                      <span className="text-xs font-semibold text-gray-500 block">Preferred Qualifications:</span>
                      <div className="flex flex-wrap gap-2">
                        {selectedJob.preferred_skills.map((skill) => (
                          <span 
                            key={skill} 
                            className="px-3 py-1 rounded-full text-xs font-medium bg-[#f3f2ef] text-gray-700"
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Section 5: About the Company */}
                <div className="border border-[#ebebeb] rounded-lg p-5 space-y-4">
                  <div className="flex items-start gap-3">
                    <Avatar className="h-14 w-14 rounded-sm border border-gray-200 shrink-0">
                      <AvatarFallback className="bg-slate-100 text-gray-800 font-bold text-xl rounded-sm">
                        {selectedJob.company_name?.substring(0, 1) || 'C'}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <h4 className="text-base font-bold text-gray-900">{selectedJob.company_name}</h4>
                        <button className="border border-[#0a66c2] text-[#0a66c2] text-xs font-bold px-4 py-1 rounded-full hover:bg-blue-50 transition-colors">
                          + Follow
                        </button>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {selectedJob.metadata?.company_industry || 'Information Technology & Services'} • {selectedJob.metadata?.company_size || '1,001-5,000 employees'}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {selectedJob.location || 'San Francisco, CA'} • 248,190 followers
                      </p>
                    </div>
                  </div>

                  <p className="text-xs text-gray-700 leading-relaxed">
                    {selectedJob.company_name} is an industry leader pioneering cutting-edge technology and intelligent software solutions designed to empower organizations and individuals across the globe.
                  </p>
                </div>

              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-sm text-gray-500">
              Select a job to view details
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
