#!/usr/bin/env python3
"""
Security Scanner for OpenAI API Keys and Sensitive Information
==============================================================

This script comprehensively scans the repository for:
1. OpenAI API keys (current and historical)
2. Other API keys and secrets
3. Environment variables with sensitive data
4. Configuration files with secrets

Usage: python security_scan.py
"""

import os
import re
import subprocess
import json
from datetime import datetime
from typing import List, Dict, Tuple, Set
import sys

class SecurityScanner:
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self.findings = []
        self.git_findings = []
        
        # Patterns for different types of secrets
        self.patterns = {
            'openai_api_key': [
                r'sk-[a-zA-Z0-9]{32,}',  # OpenAI API keys
                r'sk-proj-[a-zA-Z0-9_-]{64,}',  # Project API keys
            ],
            'openai_vars': [
                r'OPENAI_API_KEY\s*=\s*["\'][^"\']+["\']',
                r'openai_api_key\s*=\s*["\'][^"\']+["\']',
                r'api_key\s*=\s*["\']sk-[^"\']+["\']',
            ],
            'other_api_keys': [
                r'GROQ_API_KEY\s*=\s*["\'][^"\']+["\']',
                r'OPENROUTER_API_KEY\s*=\s*["\'][^"\']+["\']',
                r'ANTHROPIC_API_KEY\s*=\s*["\'][^"\']+["\']',
                r'GOOGLE_API_KEY\s*=\s*["\'][^"\']+["\']',
                r'COHERE_API_KEY\s*=\s*["\'][^"\']+["\']',
            ],
            'general_secrets': [
                r'password\s*=\s*["\'][^"\']+["\']',
                r'secret\s*=\s*["\'][^"\']+["\']',
                r'token\s*=\s*["\'][^"\']+["\']',
                r'key\s*=\s*["\'][a-zA-Z0-9]{20,}["\']',
            ]
        }
        
        # File extensions to scan
        self.scan_extensions = {
            '.py', '.json', '.yaml', '.yml', '.env', '.txt', 
            '.md', '.toml', '.ini', '.cfg', '.conf', '.js', 
            '.ts', '.jsx', '.tsx', '.ipynb'
        }
        
        # Files to always check regardless of extension
        self.scan_files = {
            '.env', '.env.local', '.env.production', '.env.development',
            '.env.staging', 'config', 'settings', 'secrets'
        }

    def should_scan_file(self, filepath: str) -> bool:
        """Determine if a file should be scanned."""
        if filepath.startswith('.git/'):
            return False
            
        filename = os.path.basename(filepath)
        _, ext = os.path.splitext(filepath)
        
        return (ext.lower() in self.scan_extensions or 
                filename.lower() in self.scan_files or
                any(pattern in filename.lower() for pattern in ['env', 'config', 'secret', 'key']))

    def scan_file_content(self, filepath: str) -> List[Dict]:
        """Scan file content for sensitive patterns."""
        findings = []
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            for category, patterns in self.patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # Get line number
                        line_num = content[:match.start()].count('\n') + 1
                        
                        # Get the line content
                        lines = content.split('\n')
                        line_content = lines[line_num - 1] if line_num <= len(lines) else ""
                        
                        findings.append({
                            'type': 'file_content',
                            'category': category,
                            'file': filepath,
                            'line': line_num,
                            'match': match.group(),
                            'line_content': line_content.strip(),
                            'pattern': pattern,
                            'severity': self.get_severity(category, match.group())
                        })
                        
        except Exception as e:
            print(f"Error scanning {filepath}: {e}")
            
        return findings

    def get_severity(self, category: str, match: str) -> str:
        """Determine severity of finding."""
        if category == 'openai_api_key':
            if 'sk-' in match and len(match) > 40:
                return 'CRITICAL'
            return 'HIGH'
        elif category == 'openai_vars' and any(x in match for x in ['sk-', 'proj-']):
            return 'CRITICAL'
        elif category == 'other_api_keys':
            return 'HIGH'
        else:
            return 'MEDIUM'

    def scan_git_history(self) -> List[Dict]:
        """Scan git history for sensitive information."""
        git_findings = []
        
        try:
            # Search for OpenAI API key patterns in git history
            for category, patterns in self.patterns.items():
                for pattern in patterns:
                    try:
                        # Use git log -S to search for content changes
                        cmd = ['git', 'log', '--all', '-S', pattern.replace('\\', ''), '--oneline']
                        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.repo_path)
                        
                        if result.returncode == 0 and result.stdout.strip():
                            commits = result.stdout.strip().split('\n')
                            for commit_line in commits:
                                if commit_line:
                                    commit_hash = commit_line.split()[0]
                                    commit_msg = ' '.join(commit_line.split()[1:])
                                    
                                    # Get the actual diff to see what was added/removed
                                    diff_cmd = ['git', 'show', commit_hash]
                                    diff_result = subprocess.run(diff_cmd, capture_output=True, text=True, cwd=self.repo_path)
                                    
                                    if diff_result.returncode == 0:
                                        # Look for the pattern in the diff
                                        matches = re.finditer(pattern, diff_result.stdout, re.IGNORECASE)
                                        for match in matches:
                                            git_findings.append({
                                                'type': 'git_history',
                                                'category': category,
                                                'commit': commit_hash,
                                                'message': commit_msg,
                                                'match': match.group(),
                                                'pattern': pattern,
                                                'severity': self.get_severity(category, match.group())
                                            })
                                            
                    except subprocess.SubprocessError as e:
                        print(f"Git command failed for pattern {pattern}: {e}")
                        
        except Exception as e:
            print(f"Error scanning git history: {e}")
            
        return git_findings

    def scan_current_files(self) -> List[Dict]:
        """Scan all current files in the repository."""
        findings = []
        
        for root, dirs, files in os.walk(self.repo_path):
            # Skip .git directory
            if '.git' in dirs:
                dirs.remove('.git')
                
            for file in files:
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, self.repo_path)
                
                if self.should_scan_file(rel_path):
                    file_findings = self.scan_file_content(filepath)
                    findings.extend(file_findings)
                    
        return findings

    def run_scan(self) -> Dict:
        """Run complete security scan."""
        print("🔍 Starting comprehensive security scan...")
        print(f"📁 Scanning repository: {os.path.abspath(self.repo_path)}")
        
        # Scan current files
        print("\n📄 Scanning current files...")
        current_findings = self.scan_current_files()
        
        # Scan git history
        print("📜 Scanning git history...")
        git_findings = self.scan_git_history()
        
        # Combine all findings
        all_findings = current_findings + git_findings
        
        # Generate summary
        summary = self.generate_summary(all_findings)
        
        return {
            'scan_time': datetime.now().isoformat(),
            'repository': os.path.abspath(self.repo_path),
            'summary': summary,
            'findings': all_findings
        }

    def generate_summary(self, findings: List[Dict]) -> Dict:
        """Generate summary of findings."""
        summary = {
            'total_findings': len(findings),
            'by_severity': {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0},
            'by_category': {},
            'by_type': {'file_content': 0, 'git_history': 0},
            'critical_files': set(),
            'openai_keys_found': []
        }
        
        for finding in findings:
            # Count by severity
            severity = finding.get('severity', 'LOW')
            summary['by_severity'][severity] += 1
            
            # Count by category
            category = finding.get('category', 'unknown')
            summary['by_category'][category] = summary['by_category'].get(category, 0) + 1
            
            # Count by type
            finding_type = finding.get('type', 'unknown')
            summary['by_type'][finding_type] += 1
            
            # Track critical files
            if severity == 'CRITICAL':
                if 'file' in finding:
                    summary['critical_files'].add(finding['file'])
                    
            # Track OpenAI keys specifically
            if category == 'openai_api_key' or (category == 'openai_vars' and 'sk-' in finding.get('match', '')):
                summary['openai_keys_found'].append({
                    'match': finding.get('match', ''),
                    'location': finding.get('file', finding.get('commit', 'unknown')),
                    'type': finding.get('type', 'unknown')
                })
        
        # Convert set to list for JSON serialization
        summary['critical_files'] = list(summary['critical_files'])
        
        return summary

    def print_report(self, results: Dict):
        """Print formatted security report."""
        print("\n" + "="*80)
        print("🔒 SECURITY SCAN REPORT")
        print("="*80)
        
        summary = results['summary']
        findings = results['findings']
        
        print(f"📅 Scan Time: {results['scan_time']}")
        print(f"📁 Repository: {results['repository']}")
        print(f"🔍 Total Findings: {summary['total_findings']}")
        
        print("\n📊 FINDINGS BY SEVERITY:")
        for severity, count in summary['by_severity'].items():
            if count > 0:
                emoji = {'CRITICAL': '🚨', 'HIGH': '⚠️', 'MEDIUM': '🟡', 'LOW': '🔵'}
                print(f"  {emoji.get(severity, '📌')} {severity}: {count}")
        
        print("\n📈 FINDINGS BY CATEGORY:")
        for category, count in summary['by_category'].items():
            print(f"  • {category}: {count}")
        
        if summary['openai_keys_found']:
            print("\n🚨 OPENAI API KEYS FOUND:")
            for i, key_info in enumerate(summary['openai_keys_found'], 1):
                print(f"  {i}. Type: {key_info['type']}")
                print(f"     Location: {key_info['location']}")
                print(f"     Key: {key_info['match'][:20]}...")
                print()
        
        if summary['by_severity']['CRITICAL'] > 0:
            print("\n🚨 CRITICAL FINDINGS:")
            critical_findings = [f for f in findings if f.get('severity') == 'CRITICAL']
            for i, finding in enumerate(critical_findings, 1):
                print(f"\n  {i}. Category: {finding['category']}")
                if finding['type'] == 'file_content':
                    print(f"     File: {finding['file']}")
                    print(f"     Line: {finding['line']}")
                    print(f"     Content: {finding['line_content'][:100]}...")
                else:
                    print(f"     Commit: {finding['commit']}")
                    print(f"     Message: {finding['message']}")
                print(f"     Match: {finding['match']}")
        
        print("\n💡 RECOMMENDATIONS:")
        if summary['openai_keys_found']:
            print("  🔥 IMMEDIATE ACTION REQUIRED:")
            print("     1. Revoke all exposed OpenAI API keys immediately")
            print("     2. Generate new API keys")
            print("     3. Update applications with new keys via environment variables")
            print("     4. Consider git history rewriting to remove keys permanently")
        
        print("  🛡️ PREVENTION MEASURES:")
        print("     1. Use environment variables for all API keys")
        print("     2. Add *.env files to .gitignore")
        print("     3. Use pre-commit hooks to scan for secrets")
        print("     4. Regular security scans of the repository")
        print("     5. Consider using secret management tools")
        
        print("\n" + "="*80)

def main():
    """Main function to run the security scan."""
    scanner = SecurityScanner()
    results = scanner.run_scan()
    scanner.print_report(results)
    
    # Save results to file
    output_file = 'security_scan_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    
    # Exit with error code if critical findings
    if results['summary']['by_severity']['CRITICAL'] > 0:
        print("\n❌ CRITICAL SECURITY ISSUES FOUND - IMMEDIATE ACTION REQUIRED!")
        sys.exit(1)
    else:
        print("\n✅ No critical security issues found in current scan.")
        sys.exit(0)

if __name__ == "__main__":
    main()