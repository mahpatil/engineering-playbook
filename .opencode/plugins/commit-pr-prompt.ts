import type { Plugin } from "@opencode-ai/plugin";

const COMMITTABLE_STATUS = ["M ", "A ", "D ", "R100", "??"];

const CommitPRPromptPlugin: Plugin = async ({ directory, client, $ }) => {
  return {
    "tool.execute.after": async (input, output) => {
      if (input?.tool !== "bash") {
        return;
      }

      const command = (input?.args?.command as string ?? "").toLowerCase();
      const isCommitOrStage = command.includes("commit") || command.includes("add") || command.includes("stage");
      
      if (!isCommitOrStage || output?.exit_code !== 0) {
        return;
      }

      const status = await $`cd ${directory} && git status --porcelain`.text();
      
      if (!status.trim()) {
        await client.session.prompt.append(
          `\n✅ Changes committed. Ready for PR?\n`
          + `- [ ] Create PR / open PR`
        );
        return;
      }

      const stagedFiles = await $`cd ${directory} && git diff --cached --name-only`.text();
      const hasStaged = stagedFiles.trim().length > 0;

      if (hasStaged) {
        await client.session.prompt.append(
          `\n✅ Changes staged. Ready to commit and create PR?\n`
          + `- [ ] Commit changes\n- [ ] Create PR`
        );
      }
    }
  };
};

export default CommitPRPromptPlugin;