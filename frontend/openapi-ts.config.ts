import { defineConfig } from "@hey-api/openapi-ts"

export default defineConfig({
  input: "./openapi.json",
  output: "./src/client",

  plugins: [
    {
      name: "@hey-api/client-axios",
    },
    {
      name: "@hey-api/sdk",
      operations: {
        strategy: "byTags",
        containerName: "{{name}}Service",
        nesting: "operationId",
      },
    },
    {
      name: "@hey-api/schemas",
      type: "json",
    },
  ],
})
