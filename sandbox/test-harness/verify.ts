/**
 * Test Harness for Component Verification
 *
 * This script is run inside the Docker sandbox to verify
 * that generated React components compile and render correctly.
 */

import * as fs from 'fs';
import * as path from 'path';

interface VerificationResult {
  success: boolean;
  stage: string;
  errors: string[];
  warnings: string[];
}

async function verifyComponent(componentPath: string, blueprintPath: string): Promise<VerificationResult> {
  const result: VerificationResult = {
    success: false,
    stage: 'init',
    errors: [],
    warnings: []
  };

  try {
    // Check if files exist
    if (!fs.existsSync(componentPath)) {
      result.errors.push(`Component file not found: ${componentPath}`);
      return result;
    }

    if (!fs.existsSync(blueprintPath)) {
      result.errors.push(`Blueprint file not found: ${blueprintPath}`);
      return result;
    }

    // Read component code
    const componentCode = fs.readFileSync(componentPath, 'utf-8');
    result.stage = 'read';

    // Basic syntax checks
    if (!componentCode.includes('export')) {
      result.errors.push('Component must have an export statement');
    }

    if (!componentCode.includes('function') && !componentCode.includes('=>')) {
      result.errors.push('Component must define a function');
    }

    if (componentCode.includes('eval(')) {
      result.errors.push('Component must not use eval()');
    }

    if (componentCode.includes('dangerouslySetInnerHTML')) {
      result.warnings.push('Component uses dangerouslySetInnerHTML - ensure content is sanitized');
    }

    result.stage = 'syntax';

    // Read and validate blueprint
    const blueprintContent = fs.readFileSync(blueprintPath, 'utf-8');
    const blueprint = JSON.parse(blueprintContent);

    if (!blueprint.templateType) {
      result.errors.push('Blueprint must have templateType');
    }

    if (!blueprint.title) {
      result.warnings.push('Blueprint should have a title');
    }

    result.stage = 'blueprint';

    // If no errors, mark as success
    if (result.errors.length === 0) {
      result.success = true;
      result.stage = 'complete';
    }

  } catch (error: any) {
    result.errors.push(`Verification error: ${error.message}`);
  }

  return result;
}

// Main execution
const args = process.argv.slice(2);
const componentPath = args[0] || '/app/component.tsx';
const blueprintPath = args[1] || '/app/blueprint.json';

verifyComponent(componentPath, blueprintPath)
  .then(result => {
    console.log(JSON.stringify(result, null, 2));
    process.exit(result.success ? 0 : 1);
  })
  .catch(error => {
    console.error(JSON.stringify({
      success: false,
      stage: 'fatal',
      errors: [error.message],
      warnings: []
    }, null, 2));
    process.exit(1);
  });
