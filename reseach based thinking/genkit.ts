import { genkit } from 'genkit';
import { azureOpenAI, gpt4o } from 'genkitx-azure-openai';
import * as dotenv from 'dotenv';
import { logger } from 'genkit/logging';

dotenv.config();

logger.setLogLevel('debug');

export const ai = genkit({
  plugins: [
    azureOpenAI({
      apiKey: process.env.AZURE_OPENAI_API_KEY,
      endpoint: process.env.AZURE_OPENAI_ENDPOINT,
      apiVersion: process.env.AZURE_OPENAI_API_VERSION,
      deployment: process.env.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
    }),
  ],
});

export const azureOpenAIModel = gpt4o;
