"use client";

import React, { useEffect, useState } from 'react';
import SkillList from '@/components/skills/SkillList';
import SkillEditor from '@/components/skills/SkillEditor';
import GenerateSkillButton from '@/components/skills/GenerateSkillButton';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Plus, Search, Layers, Puzzle, Info } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface Skill {
  id: number;
  name: string;
  description: string;
  content: string;
  category: string;
  skill_type: string;
  compatibilities: string[];
  is_global: boolean;
  workspace_id: number | null;
  created_at: string;
  updated_at: string | null;
}

interface SkillsPageProps {
  params: { [key: string]: string | string[] | undefined };
  searchParams: { [key: string]: string | string[] | undefined };
}

const DEFAULT_CATEGORIES = [
  'General',
  'Python',
  'Frontend',
  'Backend',
  'Database',
  'Testing',
  'Security',
  'Engineering',
  'API',
  'DevOps',
  'Documentation',
  'Performance',
];

export default function SkillsPage({ params, searchParams }: SkillsPageProps) {
  const workspaceIdParam = searchParams.workspaceId;
  const workspaceId = workspaceIdParam ? Number(workspaceIdParam) : undefined;
  const [skills, setSkills] = useState<Skill[]>([]);
  const [categories, setCategories] = useState<string[]>(DEFAULT_CATEGORIES);
  const [loading, setLoading] = useState(true);
  const [showEditor, setShowEditor] = useState(false);
  const [editingSkill, setEditingSkill] = useState<Skill | null>(null);
  const [viewingSkill, setViewingSkill] = useState<Skill | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('all');

  useEffect(() => {
    fetchCategories();
  }, []);

  const fetchCategories = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/skills/categories`);
      const data = await response.json();
      if (data.length > 0) {
        setCategories(data);
      }
    } catch (error) {
      console.error('Failed to fetch categories:', error);
    }
  };

  const fetchSkills = () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (workspaceId) params.append('workspace_id', workspaceId.toString());
    if (selectedCategory) params.append('category', selectedCategory);
    if (activeTab !== 'all') {
      const type = activeTab === 'workflows' ? 'workflow' : 
                   activeTab === 'integrations' ? 'integration' : 'general';
      params.append('skill_type', type);
    }

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/skills?${params.toString()}`)
      .then((res) => res.json())
      .then((data) => {
        setSkills(data);
        setLoading(false);
      })
      .catch((error) => {
        console.error('Failed to fetch skills:', error);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchSkills();
  }, [workspaceId, selectedCategory, activeTab]);

  const handleSaveSkill = async (skill: Partial<Skill>) => {
    const url = skill.id
      ? `${process.env.NEXT_PUBLIC_API_URL}/api/skills/${skill.id}`
      : `${process.env.NEXT_PUBLIC_API_URL}/api/skills`;

    const method = skill.id ? 'PUT' : 'POST';

    const response = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: skill.name,
        description: skill.description,
        content: skill.content,
        category: skill.category,
        skill_type: skill.skill_type || 'general',
        compatibilities: skill.compatibilities || [],
        workspace_id: workspaceId || null,
        is_global: skill.is_global || false,
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to save skill');
    }

    fetchSkills();
    fetchCategories();
  };

  const handleCreateNew = () => {
    setEditingSkill(null);
    setShowEditor(true);
  };

  const handleEditSkill = (skill: Skill) => {
    setEditingSkill(skill);
    setShowEditor(true);
  };

  const handleViewSkill = (skill: Skill) => {
    setViewingSkill(skill);
  };

  const handleGenerated = () => {
    fetchSkills();
  };

  const filteredSkills = skills.filter((skill) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      skill.name.toLowerCase().includes(query) ||
      skill.description.toLowerCase().includes(query)
    );
  });

  return (
    <div className="container mx-auto py-8">
      <div className="flex flex-col space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Skills Manager</h1>
            <p className="text-muted-foreground mt-1">
              Manage expert knowledge skills for enhanced agent performance
            </p>
          </div>
          <Button onClick={handleCreateNew}>
            <Plus className="h-4 w-4 mr-2" />
            New Skill
          </Button>
        </div>

        <div className="flex flex-col md:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search skills..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <div className="flex gap-2 flex-wrap">
            <Button
              variant={selectedCategory === null ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory(null)}
            >
              All Categories
            </Button>
            {categories.slice(0, 6).map((cat) => (
              <Button
                key={cat}
                variant={selectedCategory === cat ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedCategory(cat)}
              >
                {cat}
              </Button>
            ))}
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="all">All Skills</TabsTrigger>
            <TabsTrigger value="workflows" className="flex items-center gap-2">
              <Layers className="h-4 w-4" />
              Workflows
            </TabsTrigger>
            <TabsTrigger value="integrations" className="flex items-center gap-2">
              <Puzzle className="h-4 w-4" />
              Integrations
            </TabsTrigger>
            <TabsTrigger value="general" className="flex items-center gap-2">
              <Info className="h-4 w-4" />
              General
            </TabsTrigger>
          </TabsList>
        </Tabs>

        {workspaceId && (
          <GenerateSkillButton
            workspaceId={workspaceId}
            onGenerated={handleGenerated}
          />
        )}

        <SkillList
          workspaceId={workspaceId}
          onEditSkill={handleEditSkill}
          onViewSkill={handleViewSkill}
        />

        {filteredSkills.length === 0 && !loading && (
          <div className="text-center py-12 text-zinc-500">
            <p className="text-lg mb-2">No skills found</p>
            <p className="text-sm mb-4">
              {searchQuery
                ? 'Try adjusting your search query'
                : 'Create a new skill to get started'}
            </p>
            {!searchQuery && (
              <Button onClick={handleCreateNew}>
                <Plus className="h-4 w-4 mr-2" />
                Create Your First Skill
              </Button>
            )}
          </div>
        )}
      </div>

      <SkillEditor
        skill={editingSkill}
        isOpen={showEditor}
        onClose={() => setShowEditor(false)}
        onSave={handleSaveSkill}
        workspaceId={workspaceId}
        categories={categories}
      />

      <Dialog open={!!viewingSkill} onOpenChange={() => setViewingSkill(null)}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {viewingSkill?.name}
              <Badge variant="secondary">{viewingSkill?.category}</Badge>
            </DialogTitle>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto">
            {viewingSkill && (
              <div className="prose prose-sm max-w-none">
                <p className="text-muted-foreground mb-4">
                  {viewingSkill.description}
                </p>
                <div className="bg-muted p-4 rounded-lg">
                  <pre className="whitespace-pre-wrap text-sm">
                    {viewingSkill.content}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
