import type { Plugin } from "@opencode-ai/plugin";

const NEW_WORK_KEYWORDS = [
  "create", "add", "implement", "build", "feature", "new",
  "fix", "bug", "refactor", "update", "modify", "change",
  "improve", "support", "integrate", "setup", "configure"
];

const BranchPromptPlugin: Plugin = async ({ directory, client, $ }) => {
  return {
    "session.created": async (input) => {
      const userMessage = input?.message?.content?.[0]?.text ?? "";
      const lowerMessage = userMessage.toLowerCase();
      
      const detectedNewWork = NEW_WORK_KEYWORDS.some(keyword => 
        lowerMessage.includes(keyword)
      );
      
      if (!detectedNewWork) {
        return;
      }

      const currentBranch = await $`cd ${directory} && git branch --show-current`.text();
      const trimmedBranch = currentBranch.trim();
      
      const isMainOrMaster = ["main", "master"].includes(trimmedBranch.toLowerCase());
      
      if (!isMainOrMaster) {
        return;
      }

      const recentFiles = await $`cd ${directory} && git log --oneline -5 --name-only`.text();
      const hasRecentWork = recentFiles.trim().length > 0;
      
      if (!hasRecentWork) {
        await client.session.prompt.append(
          `\n⚠️ You're on **${trimmedBranch}** but I detect you're starting new work ("${userMessage.slice(0, 50)}..."). `
          + `Would you like me to create a feature branch for this work?`
        );
        return;
      }

      const commitDate = await $`cd ${directory} && git log -1 --format=%cd`.text();
      
      const recentCommitDate = new Date(commitDate.trim());
      const daysSince = (Date.now() - recentCommitDate.getTime()) / (1000 * 60 * 60 * 24);
      
      if (daysSince > 7) {
        await client.session.prompt.append(
          `\n⚠️ You're on **${trimmedBranch}** (last commit ${Math.floor(daysSince)} days ago) but I detect new work. `
          + `Would you like me to create a feature branch for this work?`
        );
      }
    }
  };
};

export default BranchPromptPlugin;