import unittest
from unittest.mock import MagicMock
import test.sample_events as sample_events
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from taxonomy_util import TaxonomyUtil

class TestTaxonomyUtil(unittest.TestCase):
    
    def test_killdeer_taxonomy(self):
        test_file_path = os.path.join(os.path.dirname(__file__), 'resources', 'test-keywords.txt')
        taxonomy = TaxonomyUtil(test_file_path)
        
        result = taxonomy.get_taxonomy('Killdeer')
        
        self.assertEqual(result.get('species'), 'Killdeer')
        self.assertEqual(result.get('scientific_name'), 'Charadrius vociferus')
        self.assertEqual(result.get('family'), 'Plovers')
        self.assertEqual(result.get('family_latin'), 'Charadriidae')
        self.assertEqual(result.get('order'), 'CHARADRIIFORMES')

if __name__ == '__main__':
    unittest.main()
