import type { Ref } from "vue";

interface ProjectGraph {
  nodes: Array<Record<string, unknown>>;
  edges: Array<Record<string, unknown>>;
}

export function useApi() {
  const baseUrl = import.meta.env.VITE_API_URL || "/api";

  async function healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${baseUrl}/health`);
      if (!response.ok) {
        return false;
      }
      const json = await response.json();
      return json.status === "ok";
    } catch (error) {
      console.error("Health check failed", error);
      return false;
    }
  }

  async function getProjectGraph(projectId = 1): Promise<ProjectGraph> {
    const response = await fetch(`${baseUrl}/projects/${projectId}/graph`);
    if (!response.ok) {
      throw new Error(`Failed to load project graph: ${response.status}`);
    }
    return response.json();
  }

  return {
    healthCheck,
    getProjectGraph,
  };
}
