#!/usr/bin/env node
/**
 * hash-password.js
 * Generate a bcrypt hash for ADMIN_PASSWORD_HASH.
 *
 * Usage (in Replit Shell, from project root):
 *   node scripts/hash-password.js yourpassword
 *
 * Copy the output into Replit Secrets → ADMIN_PASSWORD_HASH
 */
const bcrypt = require("bcryptjs");
const password = process.argv[2];
if (!password) {
  console.error("Usage: node scripts/hash-password.js <password>");
  process.exit(1);
}
bcrypt.hash(password, 10).then((hash) => {
  console.log("\nYour bcrypt hash (paste into ADMIN_PASSWORD_HASH secret):\n");
  console.log(hash);
  console.log();
});
