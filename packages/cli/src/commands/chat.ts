import { OmniCodeClient } from '@omnicode/sdk';
import { getConfig } from './login';
import { prompt } from 'enquirer';
import chalk from 'chalk';

export async function chat(options: { workspace: string }) {
  const config = await getConfig();
  if (!config || !config.apiKey) {
    console.error(chalk.red('Not logged in. Please run `omnicode login` first.'));
    return;
  }

  const client = new OmniCodeClient(process.env.OMNICODE_API_URL || 'http://localhost:8000', config.apiKey);
  console.log(chalk.cyan('Welcome to OmniCode Interactive Chat! Type "exit" to quit.'));

  let activeTaskId: number | null = null;

  while (true) {
    const response = await prompt<{ userInput: string }>({
      type: 'input',
      name: 'userInput',
      message: 'You:'
    });

    const userInput = response.userInput;

    if (userInput.toLowerCase() === 'exit' || userInput.toLowerCase() === 'quit') {
      break;
    }

    try {
      const { task_id } = await client.tasks.create({
        workspace_id: parseInt(options.workspace),
        task_type: 'agent_run',
        payload: { 
            prompt: userInput,
        }
      });

      activeTaskId = task_id;

      await new Promise<void>((resolve, reject) => {
        const stopStream = client.tasks.streamLogs(task_id, (log) => {
          if (typeof log === 'object' && log.content) {
            process.stdout.write(`${chalk.gray(`[${log.level || 'info'}]`)} ${log.content}\n`);
          } else {
            // Some logs might be raw strings or other formats
            try {
                const parsed = typeof log === 'string' ? JSON.parse(log) : log;
                if (parsed.content) {
                    process.stdout.write(`${chalk.gray(`[${parsed.level || 'info'}]`)} ${parsed.content}\n`);
                }
            } catch {
                process.stdout.write(`${log}\n`);
            }
          }
        });

        const pollTask = setInterval(async () => {
          const task = await client.tasks.get(task_id);
          if (task.status === 'completed' || task.status === 'failed') {
            clearInterval(pollTask);
            stopStream();
            console.log(chalk.bold(`\nAgent: Task ${task.status}`));
            resolve();
          }
        }, 2000);
      });

    } catch (err) {
      console.error(chalk.red('Error:'), err);
    }
  }
}
