#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/tests"
cd "$ROOT"

move_if_exists() {
  local dest="$1"
  shift
  mkdir -p "$dest"
  for f in "$@"; do
    if [[ -f "$f" ]]; then
      mv "$f" "$dest/"
    fi
  done
}

move_if_exists unit \
  test_agent.py test_tools.py test_enterprise_memory.py \
  test_workflow_engine.py test_workflow_human_approval.py \
  test_rag_pipeline.py test_llm_provider.py test_embedding.py \
  test_vectorstore.py test_prompt_builder.py test_prompt_center.py \
  test_plugin_system.py test_scheduler.py test_model_registry.py \
  test_model_router.py test_model_cache.py test_gpu_manager.py \
  test_inference_gateway.py test_service_discovery.py test_monitoring.py \
  test_structured_logging.py test_observability_trace.py test_engineering.py \
  test_deploy_settings.py test_agent_knowledge.py test_knowledge_loader.py \
  test_manager_agent.py test_vllm_tuning.py \
  test_software_team_architecture.py test_software_team_developer.py \
  test_software_team_devops.py test_software_team_pm.py \
  test_software_team_product.py test_software_team_reviewer.py \
  test_software_team_tester.py

move_if_exists integration \
  test_mcp_ecosystem.py test_finetune.py test_lora_finetune.py test_quantization.py

move_if_exists e2e \
  test_knowledge_assistant_api.py test_software_team_full_pipeline.py \
  test_studio_api.py test_infra_dashboard.py

echo "unit: $(find unit -name 'test_*.py' | wc -l)"
echo "integration: $(find integration -name 'test_*.py' | wc -l)"
echo "e2e: $(find e2e -name 'test_*.py' | wc -l)"
echo "root leftover: $(find . -maxdepth 1 -name 'test_*.py' | wc -l)"
