import json
import unittest
from optimal_assignment import get_severity, match_skills, calculate_score, assign_tickets

class TestEdgeCases(unittest.TestCase):
    
    def test_no_available_agents(self):
        """Test when all agents are unavailable"""
        agent = {'availability_status': 'Busy', 'skills': {}, 'current_load': 0, 'experience_level': 5}
        score = calculate_score(agent, {}, 4, 1)
        self.assertEqual(score, 0)
    
    def test_no_skill_match(self):
        """Test ticket with no matching skills"""
        skills = match_skills("random unrelated text")
        self.assertEqual(len(skills), 0)
    
    def test_high_load_agent(self):
        """Test agent with very high load gets penalty"""
        agent = {'availability_status': 'Available', 'skills': {'Linux_Administration': 10}, 
                'current_load': 10, 'experience_level': 5}
        score = calculate_score(agent, {'Linux_Administration': 1}, 1, 0)
        self.assertLess(score, 0)
    
    def test_critical_severity_detection(self):
        """Test critical severity detection"""
        severity = get_severity("production database is down critical outage")
        self.assertEqual(severity, 4)
    
    def test_empty_ticket_text(self):
        """Test empty or minimal ticket content"""
        severity = get_severity("")
        skills = match_skills("")
        self.assertEqual(severity, 1)
        self.assertEqual(len(skills), 0)

if __name__ == '__main__':
    unittest.main()
