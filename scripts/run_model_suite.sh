#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir"

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is required" >&2
  exit 1
fi
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "ANTHROPIC_API_KEY is required" >&2
  exit 1
fi

openai_configs=(
  configs/model_suite/openai_gpt_5_6_sol.yaml
  configs/model_suite/openai_gpt_5.yaml
  configs/model_suite/openai_gpt_5_mini.yaml
)
anthropic_configs=(
  configs/model_suite/anthropic_opus_4_8.yaml
  configs/model_suite/anthropic_sonnet_5.yaml
  configs/model_suite/anthropic_haiku_4_5.yaml
)
output_dirs=(
  artifacts/model-suite/gpt-5.6-sol
  artifacts/model-suite/gpt-5
  artifacts/model-suite/gpt-5-mini
  artifacts/model-suite/claude-opus-4-8
  artifacts/model-suite/claude-sonnet-5
  artifacts/model-suite/claude-haiku-4-5-20251001
)

shared_random_dir=artifacts/model-suite/shared-random
shopt -s nullglob
shared_scenarios=("$shared_random_dir"/*.yaml)
if [[ "${#shared_scenarios[@]}" -eq 0 ]]; then
  echo "Generating the shared 12-scenario random corpus with OpenAI"
  UV_CACHE_DIR="${UV_CACHE_DIR:-/private/tmp/evalforge-uv-cache}" \
    uv run evalforge generate --method random --count 12 --seed 7 \
    --output "$shared_random_dir" --proposer openai --proposer-model gpt-5.6-sol
elif [[ "${#shared_scenarios[@]}" -ne 12 ]]; then
  echo "Expected 12 shared random scenarios; found ${#shared_scenarios[@]}" >&2
  exit 1
else
  echo "Reusing 12 shared validated random scenarios from $shared_random_dir"
fi

run_provider_lane() {
  local provider="$1"
  shift
  for config in "$@"; do
    echo
    echo "[$provider] Running $config"
    UV_CACHE_DIR="${UV_CACHE_DIR:-/private/tmp/evalforge-uv-cache}" \
      uv run evalforge experiment --config "$config"
  done
}

mkdir -p artifacts/model-suite/logs
openai_pid=""
anthropic_pid=""
stop_lanes() {
  [[ -n "$openai_pid" ]] && kill "$openai_pid" 2>/dev/null || true
  [[ -n "$anthropic_pid" ]] && kill "$anthropic_pid" 2>/dev/null || true
}
trap stop_lanes INT TERM

run_provider_lane openai "${openai_configs[@]}" \
  > >(tee artifacts/model-suite/logs/openai.log) 2>&1 &
openai_pid=$!
run_provider_lane anthropic "${anthropic_configs[@]}" \
  > >(tee artifacts/model-suite/logs/anthropic.log) 2>&1 &
anthropic_pid=$!

set +e
wait "$openai_pid"
openai_status=$?
wait "$anthropic_pid"
anthropic_status=$?
set -e
trap - INT TERM

if [[ "$openai_status" -ne 0 || "$anthropic_status" -ne 0 ]]; then
  echo "Model suite failed: OpenAI lane=$openai_status Anthropic lane=$anthropic_status" >&2
  exit 1
fi

compare_args=()
for output_dir in "${output_dirs[@]}"; do
  experiment_dirs=("$output_dir"/evalforge-*)
  if [[ ! -d "${experiment_dirs[0]}" ]]; then
    echo "No completed experiment found under $output_dir" >&2
    exit 1
  fi
  if [[ "${#experiment_dirs[@]}" -ne 1 ]]; then
    echo "Expected one experiment under $output_dir; found ${#experiment_dirs[@]}" >&2
    exit 1
  fi
  compare_args+=(--experiment "${experiment_dirs[0]}")
done

UV_CACHE_DIR="${UV_CACHE_DIR:-/private/tmp/evalforge-uv-cache}" \
  uv run evalforge compare "${compare_args[@]}" \
  --output artifacts/model-suite/comparison

echo
echo "Model-suite report: artifacts/model-suite/comparison/report.md"
echo "HTML report: artifacts/model-suite/comparison/report.html"
