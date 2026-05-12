#!/usr/bin/env node
import { Command } from 'commander';
import { login } from './commands/login';
import { run } from './commands/run';
import { chat } from './commands/chat';

const program = new Command();

program
  .name('omnicode')
  .description('OmniCode CLI')
  .version('0.1.0');

program
  .command('login')
  .description('Login to OmniCode')
  .action(login);

program
  .command('run <prompt>')
  .description('Run a task with a prompt')
  .option('-w, --workspace <id>', 'Workspace ID', '1')
  .action(run);

program
  .command('chat')
  .description('Start an interactive chat session')
  .option('-w, --workspace <id>', 'Workspace ID', '1')
  .action(chat);

program.parse(process.argv);
