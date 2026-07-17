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
openai_output_dirs=(
  artifacts/model-suite/gpt-5.6-sol
  artifacts/model-suite/gpt-5
  artifacts/model-suite/gpt-5-mini
)
anthropic_output_dirs=(
  artifacts/model-suite/claude-opus-4-8
  artifacts/model-suite/claude-sonnet-5
  artifacts/model-suite/claude-haiku-4-5-20251001
)
output_dirs=(
  "${openai_output_dirs[@]}"
  "${anthropic_output_dirs[@]}"
)

shared_random_dir=artifacts/model-suite/shared-random
shopt -s nullglob
shared_scenarios=("$shared_random_dir"/*.yaml)
if [[ "${#shared_scenarios[@]}" -eq 0 ]]; then
  echo "Generating the shared 12-scenario random corpus with OpenAI"
  UV_CACHE_DIR="${UV_CACHE_DIR:-/private/tmp/evalforge-uv-cache}" \
    uv run evalforge generate --method random --count 12 --seed 7 \
    --output "$shared_random_dir" --proposer openai --proposer-model gpt-5.6-sol \
    --max-attempts 36
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

count_episodes() {
  local output_dir
  {
    for output_dir in "$@"; do
      if [[ -d "$output_dir" ]]; then
        find "$output_dir" -type f -name episode.json -print
      fi
    done
  } | wc -l | tr -d ' '
}

render_progress_bar() {
  local done_count="$1"
  local total_count="$2"
  local width=24
  local filled
  local index
  local bar=""
  if [[ "$done_count" -gt "$total_count" ]]; then
    done_count="$total_count"
  fi
  filled=$((done_count * width / total_count))
  for ((index = 0; index < width; index += 1)); do
    if [[ "$index" -lt "$filled" ]]; then
      bar+="#"
    else
      bar+="-"
    fi
  done
  printf '[%s] %3d/%d' "$bar" "$done_count" "$total_count"
}

current_model() {
  local done_count="$1"
  local first="$2"
  local second="$3"
  local third="$4"
  if [[ "$done_count" -ge 108 ]]; then
    printf 'complete'
  elif [[ "$done_count" -ge 72 ]]; then
    printf '%s' "$third"
  elif [[ "$done_count" -ge 36 ]]; then
    printf '%s' "$second"
  else
    printf '%s' "$first"
  fi
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
  > artifacts/model-suite/logs/openai.log 2>&1 &
openai_pid=$!
run_provider_lane anthropic "${anthropic_configs[@]}" \
  > artifacts/model-suite/logs/anthropic.log 2>&1 &
anthropic_pid=$!

echo
echo "Provider progress (36 episodes per model; 108 per lane)"
while kill -0 "$openai_pid" 2>/dev/null || kill -0 "$anthropic_pid" 2>/dev/null; do
  openai_done="$(count_episodes "${openai_output_dirs[@]}")"
  anthropic_done="$(count_episodes "${anthropic_output_dirs[@]}")"
  printf '\rOpenAI   %s %-12s | Anthropic %s %-24s' \
    "$(render_progress_bar "$openai_done" 108)" \
    "$(current_model "$openai_done" 'GPT-5.6 Sol' 'GPT-5' 'GPT-5 mini')" \
    "$(render_progress_bar "$anthropic_done" 108)" \
    "$(current_model "$anthropic_done" 'Opus 4.8' 'Sonnet 5' 'Haiku 4.5')"
  sleep 2
done
openai_done="$(count_episodes "${openai_output_dirs[@]}")"
anthropic_done="$(count_episodes "${anthropic_output_dirs[@]}")"
printf '\rOpenAI   %s %-12s | Anthropic %s %-24s\n' \
  "$(render_progress_bar "$openai_done" 108)" \
  "$(current_model "$openai_done" 'GPT-5.6 Sol' 'GPT-5' 'GPT-5 mini')" \
  "$(render_progress_bar "$anthropic_done" 108)" \
  "$(current_model "$anthropic_done" 'Opus 4.8' 'Sonnet 5' 'Haiku 4.5')"

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
