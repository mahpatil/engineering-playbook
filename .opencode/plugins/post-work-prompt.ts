import type { Plugin } from "@opencode-ai/plugin";

const POST_WORK_KEYWORDS = [
  "run", "test", "build", "dev", "start", "serve", 
  "lint", "check", "validate", "deploy"
];

const POST_WORK_PROMPTS = [
  { check: "README", hint: "update documentation", keywords: ["readme", "doc", "usage", "install"] },
  { check: "tests", hint: "add/update tests", keywords: ["test", "spec", "fix", "bug", "feature"] },
  { check: "OpenSpec", hint: "update spec docs", keywords: ["api", "endpoint", "schema", "model", "service"] },
];

const PostWorkPromptPlugin: Plugin = async ({ directory, client, $ }) => {
  return {
    "tool.execute.after": async (input, output) => {
      if (input?.tool !== "bash") {
        return;
      }

      const command = (input?.args?.command as string ?? "").toLowerCase();
      const isRunCommand = POST_WORK_KEYWORDS.some(kw => 
        command.includes(kw)
      );

      if (!isRunCommand) {
        return;
      }

      const exitCode = output?.exit_code;
      if (exitCode !== 0) {
        await client.session.prompt.append(
          `\n⚠️ Command exited with errors. Fix first, then consider:\n`
          + `- [ ] Update tests\n- [ ] Update docs\n- [ ] Update spec`
        );
        return;
      }

      const fileList = await $`find ${directory}/.opencode -name "*.ts" -o -name "*.js" | head -20`.text();
      const hasTests = fileList.includes("test") || fileList.includes("spec");
      const hasDocs = fileList.includes("readme") || fileList.includes("doc");

      let suggestions = "";
      
      if (!hasDocs) {
        suggestions += `\n- [x] Update README (documentation)`;
      }
      if (!hasTests) {
        suggestions += `\n- [x] Update/add tests`;
      }

      const hasSpecChanges = command.includes("api") || command.includes("schema");
      if (hasSpecChanges) {
        suggestions += `\n- [x] Update OpenSpec`;
      }

      if (suggestions) {
        await client.session.prompt.append(
          `\n✅ Command succeeded! Consider post-work items:\n${suggestions}`
        );
      }
    }
  };
};

export default PostWorkPromptPlugin;