import * as acorn from 'acorn';

/**
 * Validates the generated p5.js code block against strict safety and structure constraints.
 * 
 * @param {string} code - The Javascript code block containing the buildSketch function body.
 * @param {number} [maxSize=20000] - Maximum allowed characters.
 * @returns {{valid: boolean, error?: string}}
 */
export function validateSketchCode(code, maxSize = 20000) {
  if (!code) {
    return { valid: false, error: 'Code is empty' };
  }
  if (code.length > maxSize) {
    return { valid: false, error: `Code exceeds size limit (${code.length} > ${maxSize} chars)` };
  }

  // Wrap the code in a function signature block to parse it as valid script syntax
  const wrappedCode = `function buildSketch(p, container) {\n${code}\n}`;

  let ast;
  try {
    ast = acorn.parse(wrappedCode, { ecmaVersion: 2020, sourceType: 'script' });
  } catch (err) {
    return { valid: false, error: `Syntax error: ${err.message}` };
  }

  // Forbidden globals, APIs, and properties to prevent sandbox breakouts/abuse
  const forbiddenKeys = new Set([
    'window', 'document', 'fetch', 'XMLHttpRequest', 'eval', 'Function', 
    'import', 'localStorage', 'sessionStorage', 'cookie', 'parent', 'top', 
    'opener', 'frames', 'location', 'history', 'navigator',
    'constructor', 'prototype', '__proto__'
  ]);

  let pSetupFound = false;
  let pDrawFound = false;
  let hasError = null;

  function walk(node, isSafeKey = false) {
    if (!node || hasError) return;

    // Reject static or dynamic import expressions
    if (node.type === 'ImportDeclaration' || node.type === 'ImportExpression') {
      hasError = 'Imports are forbidden';
      return;
    }

    // Check for forbidden identifiers
    if (node.type === 'Identifier') {
      if (forbiddenKeys.has(node.name)) {
        if (!(node.name === 'constructor' && isSafeKey)) {
          hasError = `Forbidden identifier referenced: "${node.name}"`;
          return;
        }
      }
    }

    // Check for property access via computed MemberExpressions, e.g. obj['window'] or obj['constructor']
    if (node.type === 'MemberExpression') {
      if (node.property.type === 'Identifier' && forbiddenKeys.has(node.property.name)) {
        hasError = `Forbidden property referenced: "${node.property.name}"`;
        return;
      }
      if (node.computed && node.property.type === 'Literal') {
        const val = node.property.value;
        if (typeof val === 'string' && forbiddenKeys.has(val)) {
          hasError = `Forbidden property referenced: "${val}"`;
          return;
        }
      }
    }

    // Detect setup and draw assignments on p: p.setup = ... / p.draw = ...
    if (
      node.type === 'AssignmentExpression' &&
      node.left.type === 'MemberExpression' &&
      node.left.object.type === 'Identifier' &&
      node.left.object.name === 'p' &&
      node.left.property.type === 'Identifier'
    ) {
      if (node.left.property.name === 'setup') pSetupFound = true;
      if (node.left.property.name === 'draw') pDrawFound = true;
    }

    // Traverse all child keys recursively
    for (const key in node) {
      const child = node[key];
      if (child && typeof child === 'object') {
        if (Array.isArray(child)) {
          for (const item of child) {
            if (item && item.type) {
              const childIsSafe = (
                (node.type === 'MethodDefinition' && key === 'key') ||
                (node.type === 'Property' && key === 'key' && !node.computed) ||
                (node.type === 'ClassDeclaration' && key === 'id') ||
                (node.type === 'ClassExpression' && key === 'id')
              );
              walk(item, childIsSafe);
            }
          }
        } else if (child.type) {
          const childIsSafe = (
            (node.type === 'MethodDefinition' && key === 'key') ||
            (node.type === 'Property' && key === 'key' && !node.computed) ||
            (node.type === 'ClassDeclaration' && key === 'id') ||
            (node.type === 'ClassExpression' && key === 'id')
          );
          walk(child, childIsSafe);
        }
      }
    }
  }

  walk(ast);

  if (hasError) {
    return { valid: false, error: hasError };
  }

  if (!pSetupFound) {
    return { valid: false, error: 'Missing assignment to "p.setup"' };
  }
  if (!pDrawFound) {
    return { valid: false, error: 'Missing assignment to "p.draw"' };
  }

  return { valid: true };
}
