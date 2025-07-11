import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";
import {
  StdioClientTransport,
  StdioServerParameters,
} from "@modelcontextprotocol/sdk/client/stdio.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { Transport } from "@modelcontextprotocol/sdk/shared/transport.js";

import { IOType, ServerParameters } from "./fetch-metamcp";

const sleep = (time: number) =>
  new Promise<void>((resolve) => setTimeout(() => resolve(), time));
export interface ConnectedClient {
  client: Client;
  cleanup: () => Promise<void>;
}

/**
 * Transforms localhost URLs to use host.docker.internal when running inside Docker
 */
export const transformDockerUrl = (url: string): string => {
  if (process.env.TRANSFORM_LOCALHOST_TO_DOCKER_INTERNAL === "true") {
    const transformed = url.replace(
      /localhost|127\.0\.0\.1/g,
      "host.docker.internal",
    );
    console.log(`Docker URL transformation: ${url} -> ${transformed}`);
    return transformed;
  }
  console.log(`Docker URL transformation disabled: ${url}`);
  return url;
};

export const createMetaMcpClient = (
  serverParams: ServerParameters,
): { client: Client | undefined; transport: Transport | undefined } => {
  let transport: Transport | undefined;

  // Create the appropriate transport based on server type
  // Default to "STDIO" if type is undefined
  if (!serverParams.type || serverParams.type === "STDIO") {
    // Get stderr value from serverParams, environment variable, or default to "ignore"
    // TODO: improve error handling, piping and reporting
    const _stderrValue: IOType = "pipe";

    const stdioParams: StdioServerParameters = {
      command: serverParams.command || "",
      args: serverParams.args || undefined,
      env: serverParams.env || undefined,
      stderr: "ignore",
    };
    transport = new StdioClientTransport(stdioParams);

    // Handle stderr stream when set to "pipe"
    // if ((transport as StdioClientTransport).stderr) {
    //   const stderrStream = (transport as StdioClientTransport).stderr;

    //   stderrStream?.on("data", (chunk: Buffer) => {
    //     console.error(`[${serverParams.name}] ${chunk.toString().trim()}`);
    //   });

    //   stderrStream?.on("error", (error: Error) => {
    //     console.error(`[${serverParams.name}] stderr error:`, error);
    //   });
    // }
  } else if (serverParams.type === "SSE" && serverParams.url) {
    // Transform the URL if TRANSFORM_LOCALHOST_TO_DOCKER_INTERNAL is set to "true"
    const transformedUrl = transformDockerUrl(serverParams.url);
    console.log(`Creating SSE transport for: ${transformedUrl}`);

    if (!serverParams.oauth_tokens) {
      transport = new SSEClientTransport(new URL(transformedUrl));
    } else {
      const headers: Record<string, string> = {};
      headers["Authorization"] =
        `Bearer ${serverParams.oauth_tokens.access_token}`;
      transport = new SSEClientTransport(new URL(transformedUrl), {
        requestInit: {
          headers,
        },
        eventSourceInit: {
          fetch: (url, init) => fetch(url, { ...init, headers }),
        },
      });
    }
  } else if (serverParams.type === "STREAMABLE_HTTP" && serverParams.url) {
    // Transform the URL if TRANSFORM_LOCALHOST_TO_DOCKER_INTERNAL is set to "true"
    const transformedUrl = transformDockerUrl(serverParams.url);
    console.log(`Creating StreamableHTTP transport for: ${transformedUrl}`);

    if (!serverParams.oauth_tokens) {
      transport = new StreamableHTTPClientTransport(new URL(transformedUrl));
    } else {
      const headers: Record<string, string> = {};
      headers["Authorization"] =
        `Bearer ${serverParams.oauth_tokens.access_token}`;
      transport = new StreamableHTTPClientTransport(new URL(transformedUrl), {
        requestInit: {
          headers,
        },
      });
    }
  } else {
    console.error(`Unsupported server type: ${serverParams.type}`);
    return { client: undefined, transport: undefined };
  }

  const client = new Client(
    {
      name: "metamcp-client",
      version: "2.0.0",
    },
    {
      capabilities: {
        prompts: {},
        resources: { subscribe: true },
        tools: {},
      },
    },
  );
  return { client, transport };
};

export const connectMetaMcpClient = async (
  client: Client,
  transport: Transport,
): Promise<ConnectedClient | undefined> => {
  const waitFor = 2500;
  const retries = 3;
  let count = 0;
  let retry = true;

  while (retry) {
    try {
      await client.connect(transport);

      return {
        client,
        cleanup: async () => {
          await transport.close();
          await client.close();
        },
      };
    } catch (error) {
      console.error(`Error connecting to MetaMCP client: ${error}`);
      count++;
      retry = count < retries;
      if (retry) {
        try {
          await client.close();
        } catch {
          /* empty */
        }
        await sleep(waitFor);
      }
    }
  }
};
