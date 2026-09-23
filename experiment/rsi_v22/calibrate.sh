#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOST="$ROOT/host"
V22="$ROOT/experiment/rsi_v22"
TEST_DIR="$HOST/src/test/java/be/mjodheim/brewstead/service"

calibrate() {
  local label="$1"
  local patch="$2"
  local public_test="$3"
  local reserved_test="$4"
  local evaluator_source="$5"
  local production_source="$6"

  echo "=== CALIBRATE $label ==="
  cp "$V22/evaluator/$evaluator_source" "$TEST_DIR/$evaluator_source"

  pushd "$HOST" >/dev/null
  git apply "$V22/$patch"

  echo "[1/3] defect must pass public guard: $public_test"
  ./mvnw -q -Dtest="$public_test" test

  echo "[2/3] defect must fail reserved objective: $reserved_test"
  set +e
  ./mvnw -q -Dtest="$reserved_test" test
  local defect_reserved_status=$?
  set -e
  if [ "$defect_reserved_status" -eq 0 ]; then
    echo "CALIBRATION FAILURE: defect unexpectedly passed reserved objective" >&2
    exit 31
  fi

  git checkout -- "$production_source"

  echo "[3/3] oracle must pass reserved objective: $reserved_test"
  ./mvnw -q -Dtest="$reserved_test" test

  git apply --check "$V22/$patch"
  popd >/dev/null

  echo "CALIBRATION_TASK=PASS $label"
}

python3 -m py_compile "$V22/utility.py"

calibrate   "brewstead-game-state-estate-max-fields"   "defects/game-state-estate-max-fields.patch"   "GameStateServiceTest"   "GameStateEstateReservedTest"   "GameStateEstateReservedTest.java"   "src/main/java/be/mjodheim/brewstead/service/GameStateService.java"

calibrate   "brewstead-progression-merchant-coin-bonus"   "defects/progression-merchant-coin-bonus.patch"   "ProgressionServiceTest"   "ProgressionMerchantReservedTest"   "ProgressionMerchantReservedTest.java"   "src/main/java/be/mjodheim/brewstead/service/ProgressionService.java"

calibrate   "brewstead-catalog-crop-ingredient-name"   "defects/catalog-crop-ingredient-name.patch"   "CatalogServiceTest"   "CatalogCropIngredientReservedTest"   "CatalogCropIngredientReservedTest.java"   "src/main/java/be/mjodheim/brewstead/service/CatalogService.java"

echo "GENESIS_RSI_V22_CALIBRATION=PASS"
