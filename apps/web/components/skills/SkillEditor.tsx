"use client";

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';

interface Skill {
  id?: number;
  name: string;
  description: string;
  content: string;
  category: string;
  skill_type: string;
  compatibilities: string[];
  workspace_id?: number | null;
  is_global?: boolean;
}

interface SkillEditorProps {
  skill: Skill | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (skill: Skill) => void;
  workspaceId?: number;
  categories: string[];
}

export default function SkillEditor({
  skill,
  isOpen,
  onClose,
  onSave,
  workspaceId,
  categories,
}: SkillEditorProps) {
  const [formData, setFormData] = useState<Skill>({
    name: '',
    description: '',
    content: '',
    category: 'General',
    skill_type: 'general',
    compatibilities: [],
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (skill) {
      setFormData({
        id: skill.id,
        name: skill.name,
        description: skill.description,
        content: skill.content,
        category: skill.category,
        skill_type: skill.skill_type || 'general',
        compatibilities: skill.compatibilities || [],
        workspace_id: skill.workspace_id,
        is_global: skill.is_global,
      });
    } else {
      setFormData({
        name: '',
        description: '',
        content: '',
        category: 'General',
        skill_type: 'general',
        compatibilities: [],
        workspace_id: workspaceId || null,
        is_global: false,
      });
    }
  }, [skill, workspaceId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    try {
      await onSave(formData);
      onClose();
    } catch (error) {
      console.error('Failed to save skill:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>
            {skill?.id ? 'Edit Skill' : 'Create New Skill'}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex-1 overflow-hidden flex flex-col">
          <div className="flex-1 overflow-y-auto space-y-4 p-1">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1 block">
                  Skill Name
                </label>
                <Input
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="e.g., python_expert"
                  required
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">
                  Category
                </label>
                <select
                  name="category"
                  value={formData.category}
                  onChange={handleChange}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                >
                  {categories.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1 block">
                  Skill Type
                </label>
                <select
                  name="skill_type"
                  value={formData.skill_type}
                  onChange={handleChange}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                >
                  <option value="general">General</option>
                  <option value="workflow">Workflow</option>
                  <option value="integration">Integration</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">
                  Compatibility (comma separated)
                </label>
                <Input
                  name="compatibilities"
                  value={formData.compatibilities.join(', ')}
                  onChange={(e) => {
                    const values = e.target.value.split(',').map(s => s.trim()).filter(s => s !== '');
                    setFormData(prev => ({ ...prev, compatibilities: values }));
                  }}
                  placeholder="e.g., warp, github, vercel"
                />
              </div>
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">
                Description
              </label>
              <Input
                name="description"
                value={formData.description}
                onChange={handleChange}
                placeholder="Brief description of this skill..."
                required
              />
            </div>

            <div className="flex items-center gap-4">
              <label className="text-sm font-medium flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.is_global}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      is_global: e.target.checked,
                    }))
                  }
                  className="rounded"
                />
                Global Skill (available to all workspaces)
              </label>
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">
                Content (Markdown)
              </label>
              <Textarea
                name="content"
                value={formData.content}
                onChange={handleChange}
                placeholder="Write your skill content in Markdown..."
                className="min-h-[400px] font-mono text-sm"
                required
              />
            </div>

            <div className="bg-muted/50 rounded-lg p-4 text-sm">
              <p className="font-medium mb-2">Markdown Tips:</p>
              <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                <li>Use # for headings</li>
                <li>Use ``` for code blocks</li>
                <li>Use **text** for bold</li>
                <li>Use - for bullet points</li>
              </ul>
            </div>
          </div>

          <DialogFooter className="mt-4 pt-4 border-t">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? 'Saving...' : 'Save Skill'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
