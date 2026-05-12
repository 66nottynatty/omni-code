'use client';

import React, { useEffect, useState } from 'react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { ChevronDown, Check } from 'lucide-react';

interface Model {
  id: string;
  name: string;
  provider: string;
  context_window: string;
  cost_tier: 'free' | 'pro' | 'enterprise';
}

export default function ModelPicker() {
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState<Model | null>(null);

  useEffect(() => {
    const fetchModels = async () => {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/models`);
      if (res.ok) {
        const data = await res.json();
        setModels(data);
        const saved = localStorage.getItem('selectedModel');
        if (saved) {
          const parsed = JSON.parse(saved);
          setSelectedModel(data.find((m: Model) => m.id === parsed.id) || data[0]);
        } else if (data.length > 0) {
          setSelectedModel(data[0]);
        }
      }
    };
    fetchModels();
  }, []);

  const handleSelect = (model: Model) => {
    setSelectedModel(model);
    localStorage.setItem('selectedModel', JSON.stringify(model));
  };

  const groupedModels = models.reduce((acc, model) => {
    if (!acc[model.provider]) acc[model.provider] = [];
    acc[model.provider].push(model);
    return acc;
  }, {} as Record<string, Model[]>);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="w-[200px] justify-between">
          {selectedModel ? selectedModel.name : "Select Model"}
          <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-[250px]">
        {Object.entries(groupedModels).map(([provider, providerModels]) => (
          <DropdownMenuGroup key={provider}>
            <DropdownMenuLabel>{provider}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {providerModels.map((model) => (
              <DropdownMenuItem key={model.id} onClick={() => handleSelect(model)} className="flex justify-between items-center">
                <div className="flex flex-col">
                  <span className="flex items-center gap-2">
                    {model.name}
                    {selectedModel?.id === model.id && <Check className="h-3 w-3" />}
                  </span>
                  <span className="text-[10px] text-muted-foreground">{model.context_window} context</span>
                </div>
                <Badge variant={model.cost_tier === 'free' ? 'secondary' : 'default'} className="text-[9px]">
                  {model.cost_tier}
                </Badge>
              </DropdownMenuItem>
            ))}
          </DropdownMenuGroup>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
