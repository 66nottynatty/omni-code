import { OmniCodeClient } from '@omnicode/sdk';
import { getConfig } from './login';
import chalk from 'chalk';

export async function run(prompt: string, options: { workspace: string }) {
  const config = await getConfig();
  if (!config || !config.apiKey) {
    console.error(chalk.red('Not logged in. Please run `omnicode login` first.'));
    return;
  }

  const client = new OmniCodeClient(process.env.OMNICODE_API_URL || 'http://localhost:8000', config.apiKey);

  try {
    const { task_id } = await client.tasks.create({
      workspace_id: parseInt(options.workspace),
      task_type: 'agent_run',
      payload: { prompt }
    });

    console.log(chalk.blue(`Task created: ${task_id}`));

    client.tasks.streamLogs(task_id, (log) => {
      if (typeof log === 'object' && log.content) {
        process.stdout.write(`${chalk.gray(`[${log.level || 'info'}]`)} ${log.content}\n`);
      } else {
        process.stdout.write(`${log}\n`);
      }
    });

    // We need to keep the process alive while streaming
    // and check for task completion
    const pollTask = setInterval(async () => {
      const task = await client.tasks.get(task_id);
      if (task.status === 'completed' || task.status === 'failed') {
        clearInterval(pollTask);
        console.log(chalk.bold(`\nTask ${task.status}`));
        process.exit(task.status === 'completed' ? 0 : 1);
      }
    }, 2000);

  } catch (err) {
    console.error(chalk.red('Failed to run task:'), err);
  }
}
