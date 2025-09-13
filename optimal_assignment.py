import json
import time
from concurrent.futures import ThreadPoolExecutor
import logging
from typing import Dict, List, Set
from dataclasses import dataclass
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Cache for skill keywords
SKILL_KEYWORDS = {
    'VPN_Troubleshooting': {'vpn', 'tunnel', 'remote', 'connection dropping'},
    'Microsoft_365': {'outlook', 'office', 'email', 'teams', 'sharepoint', 'onedrive'},
    'Linux_Administration': {'linux', 'permission', 'directory', 'sudo', 'chmod', 'bash'},
    'Hardware_Diagnostics': {'laptop', 'boot', 'hardware', 'screen', 'keyboard', 'battery'},
    'Active_Directory': {'active directory', 'sso', 'account', 'group policy', 'domain'},
    'Database_SQL': {'database', 'sql', 'query', 'backup', 'restore'},
    'Network_Security': {'security', 'attack', 'locked', 'firewall', 'breach'},
    'Cloud_Azure': {'azure', 'cloud', 'app service', 'saas'},
    'Networking': {'network', 'printer', 'ip', 'dns', 'dhcp'}
}

# Severity keywords cache
SEVERITY_KEYWORDS = {
    'critical': {'critical', 'down', 'outage', 'production', 'business-critical'},
    'high': {'slow', 'performance', 'security', 'widespread'},
    'medium': {'unable', 'error', 'fails'}
}

def load_data():
    with open('dataset.json', 'r') as f:
        return json.load(f)

def get_severity(text):
    text = text.lower()
    if any(word in text for word in ['critical', 'down', 'outage', 'production', 'business-critical']):
        return 4
    elif any(word in text for word in ['slow', 'performance', 'security', 'widespread']):
        return 3
    elif any(word in text for word in ['unable', 'error', 'fails']):
        return 2
    return 1

def match_skills(text: str) -> Dict[str, int]:
    """Match skills using cached keywords for better performance"""
    text = text.lower()
    text_words = set(text.split())
    
    skills = {}
    for skill, keywords in SKILL_KEYWORDS.items():
        score = sum(2 for keyword in keywords if keyword in text_words)
        if score > 0:
            skills[skill] = score
    return {k: v for k, v in skills.items() if v > 0}

def calculate_score(agent, ticket_skills, severity, age_factor):
    if agent['availability_status'] != 'Available':
        return 0
    skill_score = sum(agent['skills'].get(skill, 0) * count for skill, count in ticket_skills.items())
    exp_bonus = agent['experience_level'] * (severity / 4)
    load_penalty = agent['current_load'] * 5
    urgency_bonus = age_factor * severity
    return skill_score + exp_bonus + urgency_bonus - load_penalty

def process_ticket(ticket, current_time):
    """Process a single ticket for parallel execution"""
    text = f"{ticket['title']} {ticket['description']}"
    severity = get_severity(text)
    age_hours = (current_time - ticket['creation_timestamp']) / 3600
    priority = severity * 10 + min(age_hours, 48)
    
    return {
        'ticket': ticket,
        'severity': severity,
        'skills': match_skills(text),
        'priority': priority,
        'age_factor': min(age_hours / 24, 2)
    }

def assign_tickets():
    try:
        data = load_data()
        current_time = time.time()
        tickets = []
        
        # Process tickets in parallel for large datasets
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(process_ticket, ticket, current_time) 
                      for ticket in data['tickets']]
            tickets = [f.result() for f in futures]
            
        logging.info(f"Processed {len(tickets)} tickets in parallel")
    except Exception as e:
        logging.error(f"Error processing tickets: {str(e)}")
        raise
    
    for ticket in data['tickets']:
        text = f"{ticket['title']} {ticket['description']}"
        severity = get_severity(text)
        age_hours = (current_time - ticket['creation_timestamp']) / 3600
        priority = severity * 10 + min(age_hours, 48)
        tickets.append({
            'ticket': ticket,
            'severity': severity,
            'skills': match_skills(text),
            'priority': priority,
            'age_factor': min(age_hours / 24, 2)
        })

    tickets.sort(key=lambda x: x['priority'], reverse=True)
    assignments = []
    loads = {agent['agent_id']: agent['current_load'] for agent in data['agents']}
    
    for item in tickets:
        ticket = item['ticket']
        best_agent = None
        best_score = -1
        for agent in data['agents']:
            agent['current_load'] = loads[agent['agent_id']]
            score = calculate_score(agent, item['skills'], item['severity'], item['age_factor'])
            if score > best_score:
                best_score = score
                best_agent = agent
        if best_agent:
            loads[best_agent['agent_id']] += 1
            top_skills = [(skill, best_agent['skills'].get(skill, 0)) for skill in item['skills'].keys() if best_agent['skills'].get(skill, 0) > 0][:2]
            skill_text = ' and '.join([f"'{skill}' ({score})" for skill, score in top_skills]) if top_skills else 'general support'
            
            current_load = best_agent['current_load']
            if current_load <= 2:
                workload_text = "low workload"
            elif current_load <= 4:
                workload_text = "moderate workload"
            else:
                workload_text = "higher workload but best skill match"
                
            rationale = f"Assigned to {best_agent['name']} ({best_agent['agent_id']}) based on expertise in {skill_text} and {workload_text}."
            assignments.append({
                'ticket_id': ticket['ticket_id'],
                'title': ticket['title'],
                'assigned_agent_id': best_agent['agent_id'],
                'rationale': rationale
            })
    return assignments


def main():
    assignments = assign_tickets()
    with open('output_result.json', 'w') as f:
        json.dump(assignments, f, indent=2)
    print(f"Assigned {len(assignments)} tickets optimally!")

if __name__ == "__main__":
    main()
