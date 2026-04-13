import type { Plugin } from "@opencode-ai/plugin";

const SECRET_PATTERNS = [
  ".env",
  ".env.local",
  ".env.production",
  ".env.development",
  ".env.test",
  ".env.example",
  "secrets",
  "credentials",
  "password",
  "passwd",
  "secret",
  ".key",
  ".pem",
  ".crt",
  ".p12",
  ".pfx",
  "id_rsa",
  "id_ed25519",
  ".npmrc",
  ".pypi",
  "serviceAccountKey",
  "firebase.json"
];

const SECRET_EXTENSIONS = [
  ".env",
  ".pem",
  ".key",
  ".crt",
  ".p12",
  ".pfx",
  ".jks",
  ".keystore"
];

const SECRET_FILENAMES = [
  "secrets.yaml",
  "secrets.yml",
  "credentials.json",
  "credentials.yaml",
  "service-account.json",
  "aws-credentials",
  ".netrc",
  "htpasswd"
];

const SecretProtectionPlugin: Plugin = async ({ directory, client }) => {
  return {
    "file.read": async (input, output) => {
      const filePath = input?.filePath ?? "";
      const fileName = filePath.split("/").pop() ?? "";
      const lowerPath = filePath.toLowerCase();
      
      const isSecretFile = SECRET_FILENAMES.some(name => 
        fileName.toLowerCase() === name
      );
      
      const isSecretExt = SECRET_EXTENSIONS.some(ext => 
        lowerPath.endsWith(ext)
      );
      
      const hasSecretPattern = SECRET_PATTERNS.some(pattern => 
        lowerPath.includes(pattern.toLowerCase())
      );
      
      if (isSecretFile || isSecretExt || hasSecretPattern) {
        output.blocked = true;
        output.content = `[BLOCKED] Cannot read ${fileName} - detected as sensitive file`;
        
        await client.session.prompt.append(
          `\n⛔ Access to **${fileName}** was blocked (sensitive file detected).\n`
          + `If you need to work with this file, please access it manually or provide the content explicitly.`
        );
      }
    },
    
    "file.glob": async (input, output) => {
      const pattern = (input?.pattern ?? "").toLowerCase();
      
      const hasSecretPattern = SECRET_PATTERNS.some(p => 
        pattern.includes(p.toLowerCase())
      );
      
      if (hasSecretPattern) {
        output.files = [];
        
        await client.session.prompt.append(
          `\n⛔ Glob pattern matches sensitive files - blocked from results.`
        );
      }
    },
    
    "file.grep": async (input, output) => {
      const filePath = (input?.path ?? "").toLowerCase();
      
      const hasSecretPath = SECRET_PATTERNS.some(p => 
        filePath.includes(p.toLowerCase())
      );
      
      if (hasSecretPath) {
        output.results = [];
        
        await client.session.prompt.append(
          `\n⛔ Search in sensitive directory blocked.`
        );
      }
    }
  };
};

export default SecretProtectionPlugin;