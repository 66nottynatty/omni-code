"use client";

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Sparkles } from 'lucide-react';

interface GenerateSkillButtonProps {
  workspaceId: number;
  onGenerated: () => void;
}

export default function GenerateSkillButton({
  workspaceId,
  onGenerated,
}: GenerateSkillButtonProps) {
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/workspaces/${workspaceId}/generate-skill`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ workspace_path: '/workspace' }),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to generate workspace skill');
      }

      onGenerated();
    } catch (err) {
      setError('Failed to generate workspace profile. Please try again.');
      console.error(err);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <Card className="border-dashed">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Sparkles className="h-5 w-5" />
          Generate Workspace Profile
        </CardTitle>
        <CardDescription>
          Automatically analyze your workspace and create a custom skill with
          insights about your tech stack, dependencies, and architecture.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Button onClick={handleGenerate} disabled={generating} className="w-full">
          {generating ? (
            <>
              <span className="animate-spin mr-2">⏳</span>
              Analyzing workspace...
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4 mr-2" />
              Generate Workspace Profile
            </>
          )}
        </Button>
        {error && (
          <p className="text-sm text-destructive mt-2">{error}</p>
        )}
        <p className="text-xs text-muted-foreground mt-2">
          This will create or update a workspace_profile skill based on your
          project&apos;s package.json, requirements.txt, and file structure.
        </p>
      </CardContent>
    </Card>
  );
}
