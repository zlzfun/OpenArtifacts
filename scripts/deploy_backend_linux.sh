#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[deploy] %s\n' "$*"
}

fail() {
  printf '[deploy] ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "${script_dir}/.." && pwd)"

user_pm2_app_name="${PM2_APP_NAME-}"
user_app_host="${APP_HOST-}"
user_app_port="${APP_PORT-}"
user_domain="${DOMAIN-}"
user_nginx_server_name="${NGINX_SERVER_NAME-}"
user_nginx_bin="${NGINX_BIN-}"
user_nginx_conf_path="${NGINX_CONF_PATH-}"
user_public_base_url="${PUBLIC_BASE_URL-}"
user_open_artifacts_db="${OPEN_ARTIFACTS_DB-}"
user_open_artifacts_public_base_url="${OPEN_ARTIFACTS_PUBLIC_BASE_URL-}"
user_open_artifacts_publish_token="${OPEN_ARTIFACTS_PUBLISH_TOKEN-}"
user_setup_pm2_startup="${SETUP_PM2_STARTUP-}"
user_venv_dir="${VENV_DIR-}"
user_uv_index_url="${UV_INDEX_URL-}"
user_uv_extra_index_url="${UV_EXTRA_INDEX_URL-}"
user_uv_insecure_host="${UV_INSECURE_HOST-}"
user_pip_index_url="${PIP_INDEX_URL-}"
user_pip_extra_index_url="${PIP_EXTRA_INDEX_URL-}"

DEPLOY_CONFIG="${DEPLOY_CONFIG:-${script_dir}/deploy_backend_linux.conf}"
DEPLOY_CONFIG_EXAMPLE="${DEPLOY_CONFIG_EXAMPLE:-${script_dir}/deploy_backend_linux.example.conf}"

require_command uv
require_command sudo
UV_BIN="$(command -v uv)"

ensure_deploy_config() {
  if [[ -f "${DEPLOY_CONFIG}" ]]; then
    return
  fi
  if [[ ! -f "${DEPLOY_CONFIG_EXAMPLE}" ]]; then
    fail "deploy config not found: ${DEPLOY_CONFIG}; example not found: ${DEPLOY_CONFIG_EXAMPLE}"
  fi
  cp "${DEPLOY_CONFIG_EXAMPLE}" "${DEPLOY_CONFIG}"
  log "created local deploy config: ${DEPLOY_CONFIG}"
}

source_deploy_config() {
  if [[ -f "${DEPLOY_CONFIG}" ]]; then
    # shellcheck disable=SC1090
    set -a
    source "${DEPLOY_CONFIG}"
    set +a
  fi
}

make_project_path() {
  case "$1" in
    /*) printf '%s\n' "$1" ;;
    *) printf '%s/%s\n' "${project_dir}" "$1" ;;
  esac
}

resolve_path_defaults() {
  NGINX_CONF_PATH="${NGINX_CONF_PATH:-/etc/nginx/conf.d/open-artifacts.conf}"
  NODE_VERSION="${NODE_VERSION:-22.11.0}"
  PM2_VERSION="${PM2_VERSION:-latest}"
  DEPLOY_DIR="$(make_project_path "${DEPLOY_DIR:-.deploy}")"
  DATA_DIR="$(make_project_path "${DATA_DIR:-.data}")"
  VENV_DIR="$(make_project_path "${VENV_DIR:-.venv}")"
  TOOLS_DIR="${TOOLS_DIR:-${DEPLOY_DIR}/tools}"
  ENV_FILE="${ENV_FILE:-${DEPLOY_DIR}/open-artifacts.env}"
  RUNNER_PATH="${RUNNER_PATH:-${DEPLOY_DIR}/run-open-artifacts.sh}"
  NODEENV_DIR="${NODEENV_DIR:-${TOOLS_DIR}/nodeenv}"
  LOCAL_PM2_PREFIX="${LOCAL_PM2_PREFIX:-${TOOLS_DIR}/pm2}"
}

ensure_deploy_config
source_deploy_config

resolve_path_defaults

mkdir -p "${DEPLOY_DIR}" "${DATA_DIR}" "${TOOLS_DIR}"

saved_open_artifacts_publish_token=""

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "${ENV_FILE}"
  set +a
  saved_open_artifacts_publish_token="${OPEN_ARTIFACTS_PUBLISH_TOKEN:-}"
fi

source_deploy_config
resolve_path_defaults

PM2_APP_NAME="${user_pm2_app_name:-${PM2_APP_NAME:-open-artifacts-backend}}"
APP_HOST="${user_app_host:-${APP_HOST:-127.0.0.1}}"
APP_PORT="${user_app_port:-${APP_PORT:-8787}}"
NGINX_SERVER_NAME="${user_nginx_server_name:-${NGINX_SERVER_NAME:-${user_domain:-${DOMAIN:-_}}}}"
NGINX_CONF_PATH="${user_nginx_conf_path:-${NGINX_CONF_PATH:-/etc/nginx/conf.d/open-artifacts.conf}}"
SETUP_PM2_STARTUP="${user_setup_pm2_startup:-${SETUP_PM2_STARTUP:-0}}"
VENV_DIR="$(make_project_path "${user_venv_dir:-${VENV_DIR:-.venv}}")"
UV_INDEX_URL="${user_uv_index_url:-${UV_INDEX_URL:-${user_pip_index_url:-${PIP_INDEX_URL:-}}}}"
UV_EXTRA_INDEX_URL="${user_uv_extra_index_url:-${UV_EXTRA_INDEX_URL:-${user_pip_extra_index_url:-${PIP_EXTRA_INDEX_URL:-}}}}"
UV_INSECURE_HOST="${user_uv_insecure_host:-${UV_INSECURE_HOST:-}}"

if [[ -n "${user_nginx_bin}" ]]; then
  NGINX_BIN="${user_nginx_bin}"
elif [[ -n "${NGINX_BIN:-}" ]]; then
  NGINX_BIN="${NGINX_BIN}"
elif command -v nginx >/dev/null 2>&1; then
  NGINX_BIN="$(command -v nginx)"
elif [[ -x /usr/sbin/nginx ]]; then
  NGINX_BIN="/usr/sbin/nginx"
else
  fail "required command not found: nginx"
fi

if [[ "${NGINX_SERVER_NAME}" == "_" ]]; then
  default_public_base_url="http://localhost"
else
  default_public_base_url="http://${NGINX_SERVER_NAME}"
fi

OPEN_ARTIFACTS_DB="${user_open_artifacts_db:-${OPEN_ARTIFACTS_DB:-${DATA_DIR}/open-artifacts.sqlite3}}"
OPEN_ARTIFACTS_PUBLIC_BASE_URL="${user_open_artifacts_public_base_url:-${OPEN_ARTIFACTS_PUBLIC_BASE_URL:-${user_public_base_url:-${PUBLIC_BASE_URL:-${default_public_base_url}}}}}"
OPEN_ARTIFACTS_PUBLISH_TOKEN="${user_open_artifacts_publish_token:-${OPEN_ARTIFACTS_PUBLISH_TOKEN:-${saved_open_artifacts_publish_token}}}"

generate_token() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
  else
    "${UV_BIN}" run python -c 'import secrets; print(secrets.token_hex(32))'
  fi
}

if [[ -z "${OPEN_ARTIFACTS_PUBLISH_TOKEN}" ]]; then
  OPEN_ARTIFACTS_PUBLISH_TOKEN="$(generate_token)"
  log "generated OPEN_ARTIFACTS_PUBLISH_TOKEN in ${ENV_FILE}"
fi

write_env_file() {
  umask 077
  {
    printf 'OPEN_ARTIFACTS_DB=%q\n' "${OPEN_ARTIFACTS_DB}"
    printf 'OPEN_ARTIFACTS_PUBLIC_BASE_URL=%q\n' "${OPEN_ARTIFACTS_PUBLIC_BASE_URL}"
    printf 'OPEN_ARTIFACTS_PUBLISH_TOKEN=%q\n' "${OPEN_ARTIFACTS_PUBLISH_TOKEN}"
    printf 'APP_HOST=%q\n' "${APP_HOST}"
    printf 'APP_PORT=%q\n' "${APP_PORT}"
    printf 'VENV_DIR=%q\n' "${VENV_DIR}"
  } > "${ENV_FILE}"
}

write_runner() {
  {
    printf '#!/usr/bin/env bash\n'
    printf 'set -euo pipefail\n'
    printf 'cd %q\n' "${project_dir}"
    printf 'set -a\n'
    printf 'source %q\n' "${ENV_FILE}"
    printf 'set +a\n'
    printf 'exec "${VENV_DIR}/bin/python" -m uvicorn open_artifacts_server.app:app --app-dir server --host "${APP_HOST}" --port "${APP_PORT}"\n'
  } > "${RUNNER_PATH}"
  chmod 0755 "${RUNNER_PATH}"
}

run_nodeenv_install() {
  if command -v uvx >/dev/null 2>&1; then
    uvx --from nodeenv nodeenv --node="${NODE_VERSION}" "${NODEENV_DIR}"
  else
    "${UV_BIN}" tool run --from nodeenv nodeenv --node="${NODE_VERSION}" "${NODEENV_DIR}"
  fi
}

resolve_pm2() {
  if command -v pm2 >/dev/null 2>&1; then
    PM2_BIN="$(command -v pm2)"
    export PM2_BIN
    return
  fi

  if [[ ! -x "${NODEENV_DIR}/bin/npm" ]]; then
    log "pm2/npm not found; bootstrapping Node ${NODE_VERSION} with uv and nodeenv"
    run_nodeenv_install
  fi

  export PATH="${NODEENV_DIR}/bin:${LOCAL_PM2_PREFIX}/node_modules/.bin:${PATH}"

  if [[ ! -x "${LOCAL_PM2_PREFIX}/node_modules/.bin/pm2" ]]; then
    log "installing PM2 ${PM2_VERSION} under ${LOCAL_PM2_PREFIX}"
    "${NODEENV_DIR}/bin/npm" install --prefix "${LOCAL_PM2_PREFIX}" "pm2@${PM2_VERSION}"
  fi

  PM2_BIN="${LOCAL_PM2_PREFIX}/node_modules/.bin/pm2"
  export PM2_BIN
}

install_python_dependencies() {
  local uv_pip_args
  log "installing Python dependencies with uv pip install -e ."
  mkdir -p "$(dirname "${VENV_DIR}")"
  if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    "${UV_BIN}" venv "${VENV_DIR}"
  fi

  (
    cd "${project_dir}"
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
    uv_pip_args=(pip install)
    if [[ -n "${UV_INDEX_URL}" ]]; then
      uv_pip_args+=(--index-url "${UV_INDEX_URL}")
    fi
    if [[ -n "${UV_EXTRA_INDEX_URL}" ]]; then
      uv_pip_args+=(--extra-index-url "${UV_EXTRA_INDEX_URL}")
    fi
    if [[ -n "${UV_INSECURE_HOST}" ]]; then
      uv_pip_args+=(--allow-insecure-host "${UV_INSECURE_HOST}")
    fi
    uv_pip_args+=(-e .)
    "${UV_BIN}" "${uv_pip_args[@]}"
  )
}

start_pm2_process() {
  log "starting ${PM2_APP_NAME} with PM2"
  if "${PM2_BIN}" describe "${PM2_APP_NAME}" >/dev/null 2>&1; then
    "${PM2_BIN}" restart "${PM2_APP_NAME}" --update-env
  else
    "${PM2_BIN}" start "${RUNNER_PATH}" --name "${PM2_APP_NAME}" --interpreter bash --time
  fi
  "${PM2_BIN}" save

  if [[ "${SETUP_PM2_STARTUP}" == "1" ]]; then
    log "configuring PM2 startup for user $(id -un)"
    sudo env PATH="${PATH}" "${PM2_BIN}" startup systemd -u "$(id -un)" --hp "${HOME}"
    "${PM2_BIN}" save
  fi
}

render_nginx_config() {
  local target="$1"
  cat > "${target}" <<NGINX
server {
    listen 80;
    server_name ${NGINX_SERVER_NAME};

    client_max_body_size 20m;

    location / {
        proxy_pass http://${APP_HOST}:${APP_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
NGINX
}

reload_nginx_if_needed() {
  local tmp_conf
  local backup_conf=""
  tmp_conf="$(mktemp)"
  render_nginx_config "${tmp_conf}"

  if sudo test -f "${NGINX_CONF_PATH}" && sudo cmp -s "${tmp_conf}" "${NGINX_CONF_PATH}"; then
    log "nginx config unchanged: ${NGINX_CONF_PATH}"
    sudo "${NGINX_BIN}" -t
    return
  fi

  if sudo test -f "${NGINX_CONF_PATH}"; then
    backup_conf="$(mktemp)"
    sudo cp "${NGINX_CONF_PATH}" "${backup_conf}"
  fi

  log "installing nginx config to ${NGINX_CONF_PATH}"
  sudo install -m 0644 "${tmp_conf}" "${NGINX_CONF_PATH}"

  if ! sudo "${NGINX_BIN}" -t; then
    if [[ -n "${backup_conf}" ]]; then
      log "nginx test failed; restoring previous config"
      sudo install -m 0644 "${backup_conf}" "${NGINX_CONF_PATH}"
      sudo "${NGINX_BIN}" -t || true
    else
      log "nginx test failed; removing newly installed config"
      sudo rm -f "${NGINX_CONF_PATH}"
    fi
    fail "nginx config validation failed"
  fi

  if command -v systemctl >/dev/null 2>&1 && sudo systemctl list-unit-files nginx.service >/dev/null 2>&1; then
    sudo systemctl start nginx
    sudo "${NGINX_BIN}" -s reload
  elif command -v service >/dev/null 2>&1; then
    sudo service nginx start || true
    sudo "${NGINX_BIN}" -s reload
  else
    sudo "${NGINX_BIN}" -s reload
  fi
}

main() {
  write_env_file
  write_runner
  install_python_dependencies
  resolve_pm2
  start_pm2_process
  reload_nginx_if_needed

  log "deployment complete"
  log "public base URL: ${OPEN_ARTIFACTS_PUBLIC_BASE_URL}"
  log "publish token file: ${ENV_FILE}"
}

main "$@"
