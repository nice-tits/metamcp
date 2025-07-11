import { McpServerStatusEnum } from "@repo/zod-types";
import { and, eq } from "drizzle-orm";

import { db } from "../../db/index";
import { oauthSessionsRepository } from "../../db/repositories/index";
import { mcpServersTable, namespaceServerMappingsTable } from "../../db/schema";
import { getDefaultEnvironment } from "./utils";

// Define IOType for stderr handling
export type IOType = "overlapped" | "pipe" | "ignore" | "inherit";

// Define a new interface for server parameters that can be STDIO, SSE or STREAMABLE_HTTP
export interface ServerParameters {
  uuid: string;
  name: string;
  description: string;
  type?: "STDIO" | "SSE" | "STREAMABLE_HTTP"; // Optional field, defaults to "STDIO" when undefined
  command?: string | null;
  args?: string[] | null;
  env?: Record<string, string> | null;
  stderr?: IOType; // Optional field for stderr handling, defaults to "ignore"
  url?: string | null;
  created_at: string;
  status: string;
  oauth_tokens?: {
    access_token: string;
    token_type: string;
    expires_in?: number | undefined;
    scope?: string | undefined;
    refresh_token?: string | undefined;
  } | null;
}

export async function getMcpServers(
  namespaceUuid: string,
  includeInactiveServers: boolean = false,
): Promise<Record<string, ServerParameters>> {
  try {
    // Build the where conditions based on includeInactiveServers flag
    const whereConditions = [
      eq(namespaceServerMappingsTable.namespace_uuid, namespaceUuid),
    ];

    // Only filter by ACTIVE status if includeInactiveServers is false
    if (!includeInactiveServers) {
      whereConditions.push(
        eq(
          namespaceServerMappingsTable.status,
          McpServerStatusEnum.Enum.ACTIVE,
        ),
      );
    }

    // Fetch MCP servers for the specific namespace using a join query
    const servers = await db
      .select({
        uuid: mcpServersTable.uuid,
        name: mcpServersTable.name,
        description: mcpServersTable.description,
        type: mcpServersTable.type,
        command: mcpServersTable.command,
        args: mcpServersTable.args,
        env: mcpServersTable.env,
        url: mcpServersTable.url,
        created_at: mcpServersTable.created_at,
        bearerToken: mcpServersTable.bearerToken,
        status: namespaceServerMappingsTable.status,
      })
      .from(mcpServersTable)
      .innerJoin(
        namespaceServerMappingsTable,
        eq(mcpServersTable.uuid, namespaceServerMappingsTable.mcp_server_uuid),
      )
      .where(and(...whereConditions));

    const serverDict: Record<string, ServerParameters> = {};
    for (const server of servers) {
      // Fetch OAuth tokens from OAuth sessions table
      const oauthSession = await oauthSessionsRepository.findByMcpServerUuid(
        server.uuid,
      );
      let oauthTokens = null;

      if (oauthSession && oauthSession.tokens) {
        oauthTokens = {
          access_token: oauthSession.tokens.access_token,
          token_type: oauthSession.tokens.token_type,
          expires_in: oauthSession.tokens.expires_in,
          scope: oauthSession.tokens.scope,
          refresh_token: oauthSession.tokens.refresh_token,
        };
      }

      const params: ServerParameters = {
        uuid: server.uuid,
        name: server.name,
        description: server.description || "",
        type: server.type || "STDIO",
        command: server.command,
        args: server.args || [],
        env: server.env || {},
        url: server.url,
        created_at:
          server.created_at?.toISOString() || new Date().toISOString(),
        status: server.status.toLowerCase(),
        oauth_tokens: oauthTokens,
      };

      // Process based on server type
      if (params.type === "STDIO") {
        if ("args" in params && !params.args) {
          params.args = undefined;
        }

        params.env = {
          ...getDefaultEnvironment(),
          ...(params.env || {}),
        };
      } else if (params.type === "SSE" || params.type === "STREAMABLE_HTTP") {
        // For SSE or STREAMABLE_HTTP servers, ensure url is present
        if (!params.url) {
          console.warn(
            `${params.type} server ${params.uuid} is missing url field, skipping`,
          );
          continue;
        }
      }

      serverDict[server.uuid] = params;
    }

    return serverDict;
  } catch (error) {
    console.error("Error fetching active MCP servers from database:", error);
    return {};
  }
}
