import React, { useState, useEffect } from 'react';
import {
  UploadCloud,
  MapPin,
  Building2,
  ExternalLink,
  Plus,
  Pencil,
  ArrowRight,
  Shield,
  CheckCircle2,
  Sparkles,
  Lock,
  GraduationCap,
  Loader2,
  FileText,
  AlertCircle,
} from 'lucide-react';
import { Avatar, AvatarFallback } from '../components/ui/Avatar';
import { getProfile, getAuthToken, getApprovedPresencePosts } from '../services/api';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function ProfilePage() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  
  const [editingTargetRoles, setEditingTargetRoles] = useState(false);
  const [newRoleInput, setNewRoleInput] = useState("");
  const [savingRoles, setSavingRoles] = useState(false);
  const [presencePosts, setPresencePosts] = useState([]);

  async function loadProfile() {
    setLoading(true);
    try {
      const data = await getProfile();
      setProfile(data);
      if (data && data.target_roles) {
        setNewRoleInput(data.target_roles.join(", "));
      }
      
      const posts = await getApprovedPresencePosts();
      setPresencePosts(posts);
    } catch (err) {
      console.error("Failed to load profile:", err);
    }
    setLoading(false);
  }

  useEffect(() => {
    loadProfile();
  }, []);

  async function handleSaveTargetRoles() {
    setSavingRoles(true);
    try {
      const rolesArray = newRoleInput.split(",").map(r => r.trim()).filter(r => r.length > 0);
      const token = getAuthToken();
      const res = await fetch(`${API_BASE}/api/v1/profiles/target-roles`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` }),
        },
        body: JSON.stringify({ target_roles: rolesArray }),
      });
      if (!res.ok) throw new Error("Failed to save roles");
      setToastMessage("Target roles updated successfully");
      setTimeout(() => setToastMessage(null), 3000);
      setEditingTargetRoles(false);
      await loadProfile();
    } catch (err) {
      console.error(err);
      setUploadError("Failed to save target roles");
      setTimeout(() => setUploadError(null), 3000);
    }
    setSavingRoles(false);
  }

  async function handleResumeUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadError(null);
    setToastMessage(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const token = getAuthToken();
      const res = await fetch(`${API_BASE}/api/v1/resumes/upload`, {
        method: 'POST',
        headers: {
          ...(token && { 'Authorization': `Bearer ${token}` }),
        },
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData?.detail || `Upload failed with status ${res.status}`);
      }

      const result = await res.json();
      const meta = result.meta || {};

      setToastMessage(
        `Resume "${file.name}" processed! Extracted ${meta.total_chunks || 0} sections and ${meta.total_claims || 0} verified claims (${meta.verified_claims || 0} verified).`
      );
      setTimeout(() => setToastMessage(null), 6000);

      // Reload the profile with the newly parsed data
      await loadProfile();
    } catch (err) {
      console.error("Resume upload failed:", err);
      setUploadError(err.message);
      setTimeout(() => setUploadError(null), 5000);
    }

    setUploading(false);
    // Reset the file input so the same file can be re-uploaded
    e.target.value = '';
  }

  // Loading state
  if (loading) {
    return (
      <div className="max-w-[1128px] mx-auto py-20 flex flex-col items-center gap-4">
        <Loader2 className="h-8 w-8 text-[#0a66c2] animate-spin" />
        <p className="text-gray-500">Loading profile...</p>
      </div>
    );
  }

  // Empty state - no resume uploaded yet
  if (!profile || !profile.full_name) {
    return (
      <div className="max-w-[600px] mx-auto py-16 flex flex-col items-center gap-6 text-center">
        <div className="h-20 w-20 bg-blue-50 rounded-full flex items-center justify-center">
          <FileText className="h-10 w-10 text-[#0a66c2]" />
        </div>
        <h1 className="text-2xl font-semibold text-black">Welcome to CareerOS</h1>
        <p className="text-gray-600 max-w-md">
          Upload your resume to get started. Our AI agents will extract your skills, 
          experience, and projects to build your verified profile.
        </p>
        <label className="cursor-pointer bg-[#0a66c2] hover:bg-[#004182] text-white font-semibold rounded-full px-8 py-3 transition-colors flex items-center gap-2">
          <input
            type="file"
            accept=".pdf,.docx,.txt"
            className="hidden"
            onChange={handleResumeUpload}
            disabled={uploading}
          />
          {uploading ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Processing Resume...
            </>
          ) : (
            <>
              <UploadCloud className="h-5 w-5" />
              Upload Resume
            </>
          )}
        </label>
        {uploadError && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-2 rounded flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            {uploadError}
          </div>
        )}
      </div>
    );
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

      {/* Upload Error */}
      {uploadError && (
        <div className="fixed bottom-6 left-6 z-50 bg-red-600 text-white text-sm px-4 py-3 rounded shadow-lg flex items-center gap-2">
          <AlertCircle className="h-4 w-4" />
          {uploadError}
        </div>
      )}

      <div className="flex flex-col lg:flex-row gap-6">
        
        {/* Main Content (Left) */}
        <div className="lg:w-[75%] space-y-4">
          
          {/* Top Profile Card */}
          <div className="bg-white border border-[#ebebeb] shadow-[0_1px_2px_rgba(0,0,0,0.08)] rounded-lg overflow-hidden relative">
            {/* Cover Image */}
            <div className="h-[200px] bg-[#a0b4b7] relative">
              <button className="absolute top-4 right-4 h-8 w-8 rounded-full bg-white flex items-center justify-center hover:bg-gray-100 transition-colors shadow-sm">
                <Pencil className="h-4 w-4 text-[#0a66c2]" />
              </button>
            </div>
            
            <div className="px-6 pb-6 relative">
              {/* Avatar */}
              <div className="absolute -top-[112px] left-6">
                <Avatar className="h-[152px] w-[152px] border-4 border-white ring-0">
                  <AvatarFallback className="bg-gray-200 text-gray-700 font-bold text-5xl">
                    {profile.full_name.split(' ').map((n) => n[0]).join('')}
                  </AvatarFallback>
                </Avatar>
              </div>
              
              {/* Right side edit button */}
              <div className="flex justify-end mt-4">
                <button className="h-8 w-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition-colors">
                  <Pencil className="h-5 w-5 text-gray-600" />
                </button>
              </div>

              {/* Profile Info */}
              <div className="mt-4 flex flex-col md:flex-row gap-4 justify-between items-start">
                <div>
                  <h1 className="text-2xl font-semibold text-black leading-tight">{profile.full_name}</h1>
                  <p className="text-base text-black mt-1 max-w-[500px]">{profile.headline}</p>
                  
                  {profile.location && (
                    <div className="text-sm text-gray-500 mt-2 flex items-center gap-2">
                      <span>{profile.location}</span>
                      <span className="text-[#0a66c2] font-semibold hover:underline cursor-pointer">Contact info</span>
                    </div>
                  )}
                </div>

                <div className="flex flex-col gap-2 mt-2 md:mt-0">
                  {profile.education && (
                    <div className="flex items-center gap-2 hover:underline cursor-pointer">
                      <GraduationCap className="h-5 w-5 text-gray-700" />
                      <span className="text-sm font-semibold text-black">{profile.education}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="mt-4 flex flex-wrap items-center gap-2">
                <button className="bg-[#0a66c2] hover:bg-[#004182] text-white font-semibold rounded-full px-4 py-1.5 transition-colors">
                  Open to
                </button>
                <button className="border border-[#0a66c2] text-[#0a66c2] font-semibold rounded-full px-4 py-1.5 hover:bg-blue-50 hover:border-2 transition-all">
                  Add profile section
                </button>
                <label className="cursor-pointer border border-gray-500 text-gray-600 font-semibold rounded-full px-4 py-1.5 hover:bg-gray-100 hover:border-gray-600 hover:border-2 transition-all flex items-center gap-1">
                  <input
                    type="file"
                    accept=".pdf,.docx,.txt"
                    className="hidden"
                    onChange={handleResumeUpload}
                    disabled={uploading}
                  />
                  {uploading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Parsing...
                    </>
                  ) : 'Upload Resume'}
                </label>
                <button className="border border-gray-500 text-gray-600 font-semibold rounded-full px-4 py-1.5 hover:bg-gray-100 hover:border-gray-600 hover:border-2 transition-all">
                  More
                </button>
              </div>

              {/* Agent Trigger Banner (OS Specific) */}
              <div className="mt-6 bg-[#eef3f8] rounded-lg p-4 flex items-center justify-between border border-[#ebebeb]">
                <div>
                  <h3 className="font-semibold text-black flex items-center gap-1">
                    <Sparkles className="h-4 w-4 text-amber-500" /> Profiling Agent
                  </h3>
                  <p className="text-sm text-gray-600">Ensure your skills are perfectly aligned for outbound outreach.</p>
                </div>
                <button className="text-[#0a66c2] font-semibold hover:underline text-sm">
                  Run Sync
                </button>
              </div>

            </div>
          </div>

          {/* About Section */}
          {profile.about && (
            <div className="bg-white border border-[#ebebeb] shadow-[0_1px_2px_rgba(0,0,0,0.08)] rounded-lg p-6 relative">
               <div className="flex justify-between items-start mb-4">
                  <h2 className="text-xl font-semibold text-black">About</h2>
                  <button className="h-8 w-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition-colors">
                    <Pencil className="h-5 w-5 text-gray-600" />
                  </button>
               </div>
               <p className="text-sm text-black leading-relaxed whitespace-pre-line">
                  {profile.about}
               </p>
            </div>
          )}

          {/* Verified Evidence (Experience/Projects) */}
          {profile.verified_evidence && profile.verified_evidence.length > 0 && (
            <div className="bg-white border border-[#ebebeb] shadow-[0_1px_2px_rgba(0,0,0,0.08)] rounded-lg p-6 relative">
              <div className="flex justify-between items-start mb-6">
                 <h2 className="text-xl font-semibold text-black">Experience & Verified Projects</h2>
                 <div className="flex items-center gap-2">
                   <button className="h-8 w-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition-colors">
                     <Plus className="h-6 w-6 text-gray-600" />
                   </button>
                   <button className="h-8 w-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition-colors">
                     <Pencil className="h-5 w-5 text-gray-600" />
                   </button>
                 </div>
              </div>

              <div className="space-y-6">
                {profile.verified_evidence.map((ev, index) => (
                  <div key={ev.id} className={`flex gap-4 ${index !== profile.verified_evidence.length - 1 ? 'pb-6 border-b border-[#ebebeb]' : ''}`}>
                    <div className="h-12 w-12 bg-gray-100 border border-gray-200 shrink-0 flex items-center justify-center text-gray-500 font-bold text-lg">
                      {ev.title.substring(0, 1)}
                    </div>
                    <div>
                      <h3 className="text-base font-semibold text-black">{ev.title}</h3>
                      {ev.date && <p className="text-sm text-black">{ev.date}</p>}
                      <p className="text-sm text-gray-500 mt-1">{ev.description}</p>
                      <div className="mt-3 flex items-center gap-1.5 text-xs text-green-700 bg-green-50 w-fit px-2 py-1 rounded">
                        <Shield className="h-3.5 w-3.5" />
                        <span className="font-semibold">Verified Source:</span> {ev.provenance}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Verified Skills */}
          {profile.verified_skills && profile.verified_skills.length > 0 && (
            <div className="bg-white border border-[#ebebeb] shadow-[0_1px_2px_rgba(0,0,0,0.08)] rounded-lg p-6 relative">
              <div className="flex justify-between items-start mb-6">
                 <h2 className="text-xl font-semibold text-black">Skills</h2>
                 <div className="flex items-center gap-2">
                   <button className="h-8 w-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition-colors">
                     <Plus className="h-6 w-6 text-gray-600" />
                   </button>
                   <button className="h-8 w-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition-colors">
                     <Pencil className="h-5 w-5 text-gray-600" />
                   </button>
                 </div>
              </div>

              <div className="space-y-4">
                {profile.verified_skills.map((sk, index) => (
                  <div key={sk.name} className={`flex flex-col gap-2 ${index !== profile.verified_skills.length - 1 ? 'pb-4 border-b border-[#ebebeb]' : ''}`}>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-semibold text-black hover:text-[#0a66c2] hover:underline cursor-pointer">
                        {sk.name}
                      </h3>
                      {sk.confidence === 'VERIFIED' && (
                         <span className="inline-flex items-center text-xs font-semibold text-green-700">
                           <CheckCircle2 className="h-3 w-3 mr-1" /> Grounded
                         </span>
                      )}
                      {sk.confidence === 'INFERRED' && (
                         <span className="inline-flex items-center text-xs font-semibold text-amber-600">
                           <Sparkles className="h-3 w-3 mr-1" /> Inferred
                         </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Avatar className="h-6 w-6 shrink-0 border border-gray-200">
                         <AvatarFallback className="bg-gray-100 text-gray-500 text-[10px]">C</AvatarFallback>
                      </Avatar>
                      <span className="text-sm text-gray-600">{sk.evidence}</span>
                    </div>
                  </div>
                ))}
              </div>
              
              <button className="mt-4 w-full py-2 border-t border-[#ebebeb] text-center text-sm font-semibold text-gray-600 hover:bg-gray-100 transition-colors rounded-b-lg -mx-6 -mb-6 px-6">
                Show all skills <ArrowRight className="inline-block h-4 w-4 ml-1" />
              </button>
            </div>
          )}

        {/* Recent Activity / Posts Section */}
        {presencePosts && presencePosts.length > 0 && (
          <div className="bg-white border border-[#ebebeb] shadow-[0_1px_2px_rgba(0,0,0,0.08)] rounded-lg p-6 relative mt-4">
            <div className="flex justify-between items-start mb-6">
              <h2 className="text-xl font-semibold text-black">Recent Activity</h2>
            </div>
            
            <div className="space-y-6">
              {presencePosts.map((post, index) => (
                <div key={post.id} className={`flex flex-col gap-4 ${index !== presencePosts.length - 1 ? 'pb-6 border-b border-[#ebebeb]' : ''}`}>
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="text-base font-semibold text-black">{post.title}</h3>
                      <p className="text-xs text-gray-500 mt-1">
                        Posted by Presence Agent • {new Date(post.updated_at || post.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <p className="text-sm text-gray-800 whitespace-pre-wrap">{post.content_body}</p>
                  
                  {post.image_url && (
                    <div className="w-full mt-2 rounded-lg overflow-hidden border border-gray-200">
                      <img src={post.image_url} alt={post.title} className="w-full h-auto object-cover max-h-[400px]" />
                    </div>
                  )}
                  
                  <div className="flex items-center gap-4 text-gray-500 text-sm font-semibold mt-2">
                    <button className="flex items-center gap-1.5 hover:bg-gray-100 px-2 py-1 rounded transition-colors">
                      Like
                    </button>
                    <button className="flex items-center gap-1.5 hover:bg-gray-100 px-2 py-1 rounded transition-colors">
                      Comment
                    </button>
                    <button className="flex items-center gap-1.5 hover:bg-gray-100 px-2 py-1 rounded transition-colors">
                      Share
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Right Column (25%) */}

        <div className="hidden lg:block lg:w-[25%] space-y-4">
          
          {/* Agent Policies (OS Specific) */}
          <div className="bg-white border border-[#ebebeb] shadow-[0_1px_2px_rgba(0,0,0,0.08)] rounded-lg p-4">
            <h2 className="text-base font-semibold text-black flex items-center gap-1.5 mb-3">
              <Lock className="h-4 w-4 text-[#0a66c2]" />
              Agent Boundaries
            </h2>
            <div className="space-y-3 text-sm text-black">
              <div>
                <span className="font-semibold text-[#0a66c2]">Zero Hallucinations:</span>
                <p className="text-gray-600 mt-0.5">Resumes trace to immutable records.</p>
              </div>
              <div>
                <span className="font-semibold text-[#0a66c2]">Scam Prevention:</span>
                <p className="text-gray-600 mt-0.5">Payment up-front jobs blocked.</p>
              </div>
              <div>
                <span className="font-semibold text-[#0a66c2]">Human Approval:</span>
                <p className="text-gray-600 mt-0.5">Outreach must be verified.</p>
              </div>
            </div>
          </div>

          {/* Target Roles */}
          <div className="bg-white border border-[#ebebeb] shadow-[0_1px_2px_rgba(0,0,0,0.08)] rounded-lg p-4">
            <div className="flex justify-between items-center mb-3">
              <h2 className="text-base font-semibold text-black">Target Roles</h2>
              <button 
                className="h-8 w-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition-colors"
                onClick={() => setEditingTargetRoles(!editingTargetRoles)}
              >
                <Pencil className="h-4 w-4 text-gray-600" />
              </button>
            </div>
            
            {editingTargetRoles ? (
              <div className="space-y-3">
                <input 
                  type="text" 
                  value={newRoleInput}
                  onChange={(e) => setNewRoleInput(e.target.value)}
                  placeholder="e.g. AI Engineer, Frontend Developer"
                  className="w-full text-sm border border-gray-300 rounded px-3 py-2 outline-none focus:border-[#0a66c2]"
                />
                <div className="flex gap-2">
                  <button 
                    onClick={handleSaveTargetRoles}
                    disabled={savingRoles}
                    className="bg-[#0a66c2] text-white text-xs font-semibold px-3 py-1.5 rounded-full hover:bg-[#004182] transition-colors"
                  >
                    {savingRoles ? "Saving..." : "Save Roles"}
                  </button>
                  <button 
                    onClick={() => {
                      setEditingTargetRoles(false);
                      setNewRoleInput((profile?.target_roles || []).join(", "));
                    }}
                    className="bg-gray-100 text-gray-700 text-xs font-semibold px-3 py-1.5 rounded-full hover:bg-gray-200 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                {profile.target_roles && profile.target_roles.length > 0 ? (
                  profile.target_roles.map((tr) => (
                    <div key={tr} className="flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full bg-[#0a66c2]" />
                      <span className="text-sm font-medium text-black">{tr}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-gray-500">No target roles defined. Edit to add some.</p>
                )}
              </div>
            )}
          </div>

        </div>

      </div>
    </div>
  );
}
