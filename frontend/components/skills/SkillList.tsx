"use client";

import React, { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface Skill {
  id: number;
  name: string;
  description: string;
  content: string;
  category: string;
  is_global: boolean;
  workspace_id: number | null;
  created_at: string;
  updated_at: string | null;
}

interface SkillListProps {
  workspaceId?: number;
  onEditSkill: (skill: Skill) => void;
  onViewSkill: (skill: Skill) => void;
}

export default function SkillList({ workspaceId, onEditSkill, onViewSkill }: SkillListProps) {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string | null>(null);

  useEffect(() => {
    fetchSkills();
  }, [workspaceId, filter]);

  const fetchSkills = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (workspaceId) params.append('workspace_id', workspaceId.toString());
      if (filter) params.append('category', filter);

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/skills?${params.toString()}`
      );
      const data = await response.json();
      setSkills(data);
    } catch (error) {
      console.error('Failed to fetch skills:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSkill = async (skillId: number) => {
    if (!confirm('Are you sure you want to delete this skill?')) return;

    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/skills/${skillId}`, {
        method: 'DELETE',
      });
      fetchSkills();
    } catch (error) {
      console.error('Failed to delete skill:', error);
    }
  };

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      Python: 'bg-yellow-500',
      Frontend: 'bg-blue-500',
      Backend: 'bg-green-500',
      Database: 'bg-purple-500',
      Testing: 'bg-orange-500',
      Security: 'bg-red-500',
      Engineering: 'bg-gray-500',
      API: 'bg-cyan-500',
      DevOps: 'bg-pink-500',
      Documentation: 'bg-indigo-500',
      Performance: 'bg-amber-500',
      General: 'bg-slate-500',
    };
    return colors[category] || 'bg-slate-500';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (skills.length === 0) {
    return (
      <div className="text-center py-12 text-zinc-500">
        <p className="text-lg mb-2">No skills found</p>
        <p className="text-sm">Create a new skill or generate a workspace profile.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {skills.map((skill) => (
        <Card key={skill.id} className="hover:shadow-lg transition-shadow">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <CardTitle className="text-lg mb-1">{skill.name}</CardTitle>
                <div className="flex items-center gap-2 mb-2">
                  <Badge
                    variant="secondary"
                    className={`${getCategoryColor(skill.category)} text-white`}
                  >
                    {skill.category}
                  </Badge>
                  {skill.is_global && (
                    <Badge variant="outline">Global</Badge>
                  )}
                </div>
              </div>
            </div>
            <CardDescription className="line-clamp-2">
              {skill.description}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onViewSkill(skill)}
              >
                View
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onEditSkill(skill)}
              >
                Edit
              </Button>
              {!skill.is_global && (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => handleDeleteSkill(skill.id)}
                >
                  Delete
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
