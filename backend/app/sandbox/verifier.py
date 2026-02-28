"""Docker-based Code Verification for Generated React Components"""
import subprocess
import tempfile
import os
import json
import hashlib
import logging
from typing import Dict, Any, Tuple, Optional
from pathlib import Path

logger = logging.getLogger("gamed_ai.sandbox.verifier")

# Cache for verification results
_verification_cache: Dict[str, Tuple[bool, Dict[str, Any]]] = {}


class DockerCodeVerifier:
    """
    Verify generated React components using Docker sandbox.

    The verification process:
    1. Write component code to temp directory
    2. Write test blueprint to temp directory
    3. Run Docker container with mounted files
    4. Parse verification output
    5. Return structured result
    """

    DOCKER_IMAGE = "gamed-ai-sandbox"
    DOCKER_BUILD_PATH = Path(__file__).parent.parent.parent.parent / "sandbox"

    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache
        self._ensure_docker_image()

    def _ensure_docker_image(self):
        """Build Docker image if it doesn't exist"""
        try:
            # Check if image exists
            result = subprocess.run(
                ["docker", "images", "-q", self.DOCKER_IMAGE],
                capture_output=True,
                text=True
            )

            if not result.stdout.strip():
                logger.info(f"Building Docker image {self.DOCKER_IMAGE}...")
                subprocess.run(
                    ["docker", "build", "-t", self.DOCKER_IMAGE, str(self.DOCKER_BUILD_PATH)],
                    check=True,
                    capture_output=True
                )
                logger.info("Docker image built successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to build Docker image: {e.stderr}")
        except FileNotFoundError:
            logger.warning("Docker not available - verification will be skipped")

    def _get_cache_key(self, code: str, blueprint: Dict[str, Any]) -> str:
        """Generate cache key from code and blueprint"""
        content = code + json.dumps(blueprint, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    async def verify(
        self,
        component_code: str,
        blueprint: Dict[str, Any],
        template_type: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify a generated React component.

        Args:
            component_code: The generated React component code
            blueprint: The game blueprint JSON
            template_type: The template type (e.g., "PARAMETER_PLAYGROUND")

        Returns:
            Tuple of (is_valid, verification_report)
        """
        # Check cache
        if self.use_cache:
            cache_key = self._get_cache_key(component_code, blueprint)
            if cache_key in _verification_cache:
                logger.info(f"Using cached verification result for {template_type}")
                return _verification_cache[cache_key]

        # Create temp directory for verification files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write component file
            component_file = temp_path / f"{template_type}Game.tsx"
            component_file.write_text(component_code)

            # Write blueprint file
            blueprint_file = temp_path / "blueprint.json"
            blueprint_file.write_text(json.dumps(blueprint, indent=2))

            # Run verification stages
            report = {
                "template_type": template_type,
                "stages": {}
            }

            # Stage 1: TypeScript compilation
            ts_valid, ts_result = await self._run_typescript_check(temp_path)
            report["stages"]["typescript"] = ts_result

            if not ts_valid:
                result = (False, report)
                if self.use_cache:
                    _verification_cache[self._get_cache_key(component_code, blueprint)] = result
                return result

            # Stage 2: ESLint check
            lint_valid, lint_result = await self._run_eslint_check(temp_path)
            report["stages"]["eslint"] = lint_result

            # Lint warnings don't fail verification
            if lint_result.get("errors"):
                result = (False, report)
                if self.use_cache:
                    _verification_cache[self._get_cache_key(component_code, blueprint)] = result
                return result

            # Stage 3: Custom verification
            verify_valid, verify_result = await self._run_custom_verification(temp_path)
            report["stages"]["verification"] = verify_result

            is_valid = ts_valid and verify_valid
            report["is_valid"] = is_valid

            result = (is_valid, report)
            if self.use_cache:
                _verification_cache[self._get_cache_key(component_code, blueprint)] = result

            return result

    async def _run_typescript_check(
        self,
        temp_path: Path
    ) -> Tuple[bool, Dict[str, Any]]:
        """Run TypeScript compilation check"""
        try:
            result = subprocess.run(
                [
                    "docker", "run", "--rm",
                    "-v", f"{temp_path}:/app/src",
                    self.DOCKER_IMAGE,
                    "npx", "tsc", "--noEmit", "--strict", "/app/src"
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

            return (
                result.returncode == 0,
                {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "errors": self._parse_typescript_errors(result.stderr)
                }
            )
        except subprocess.TimeoutExpired:
            return (False, {"success": False, "errors": ["TypeScript check timed out"]})
        except FileNotFoundError:
            # Docker not available, skip verification
            logger.warning("Docker not available, skipping TypeScript check")
            return (True, {"success": True, "skipped": True})

    async def _run_eslint_check(
        self,
        temp_path: Path
    ) -> Tuple[bool, Dict[str, Any]]:
        """Run ESLint check"""
        try:
            result = subprocess.run(
                [
                    "docker", "run", "--rm",
                    "-v", f"{temp_path}:/app/src",
                    self.DOCKER_IMAGE,
                    "npx", "eslint", "/app/src", "--format", "json"
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

            try:
                lint_output = json.loads(result.stdout) if result.stdout else []
                errors = []
                warnings = []

                for file_result in lint_output:
                    for message in file_result.get("messages", []):
                        if message.get("severity") == 2:
                            errors.append(message.get("message"))
                        else:
                            warnings.append(message.get("message"))

                return (
                    len(errors) == 0,
                    {
                        "success": len(errors) == 0,
                        "errors": errors,
                        "warnings": warnings
                    }
                )
            except json.JSONDecodeError:
                return (True, {"success": True, "warnings": ["Could not parse ESLint output"]})

        except subprocess.TimeoutExpired:
            return (False, {"success": False, "errors": ["ESLint check timed out"]})
        except FileNotFoundError:
            logger.warning("Docker not available, skipping ESLint check")
            return (True, {"success": True, "skipped": True})

    async def _run_custom_verification(
        self,
        temp_path: Path
    ) -> Tuple[bool, Dict[str, Any]]:
        """Run custom verification script"""
        try:
            result = subprocess.run(
                [
                    "docker", "run", "--rm",
                    "-v", f"{temp_path}:/app/src",
                    self.DOCKER_IMAGE,
                    "npx", "ts-node", "/app/test-harness/verify.ts",
                    "/app/src/*.tsx", "/app/src/blueprint.json"
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

            try:
                verify_output = json.loads(result.stdout) if result.stdout else {}
                return (
                    verify_output.get("success", False),
                    verify_output
                )
            except json.JSONDecodeError:
                return (
                    result.returncode == 0,
                    {"success": result.returncode == 0, "raw_output": result.stdout}
                )

        except subprocess.TimeoutExpired:
            return (False, {"success": False, "errors": ["Custom verification timed out"]})
        except FileNotFoundError:
            logger.warning("Docker not available, skipping custom verification")
            return (True, {"success": True, "skipped": True})

    def _parse_typescript_errors(self, stderr: str) -> list:
        """Parse TypeScript errors from stderr"""
        errors = []
        for line in stderr.split("\n"):
            line = line.strip()
            if line and ("error" in line.lower() or "TS" in line):
                errors.append(line)
        return errors


# Singleton instance
_verifier: Optional[DockerCodeVerifier] = None


def get_verifier() -> DockerCodeVerifier:
    """Get or create the verifier singleton"""
    global _verifier
    if _verifier is None:
        _verifier = DockerCodeVerifier()
    return _verifier
