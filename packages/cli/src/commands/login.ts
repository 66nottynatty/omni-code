import { prompt } from 'enquirer';
import fs from 'fs-extra';
import path from 'path';
import os from 'os';
import chalk from 'chalk';

const CONFIG_PATH = path.join(os.homedir(), '.omnicode', 'config.json');

export async function login() {
  try {
    const response = await prompt<{ apiKey: string }>({
      type: 'input',
      name: 'apiKey',
      message: 'Enter your OmniCode API Key:'
    });
    const apiKey = response.apiKey;
    await fs.ensureDir(path.dirname(CONFIG_PATH));
    await fs.writeJson(CONFIG_PATH, { apiKey });
    console.log(chalk.green('Successfully logged in!'));
  } catch (err) {
    console.error(chalk.red('Login failed:'), err);
  }
}

export async function getConfig() {
  if (await fs.pathExists(CONFIG_PATH)) {
    return fs.readJson(CONFIG_PATH);
  }
  return null;
}
