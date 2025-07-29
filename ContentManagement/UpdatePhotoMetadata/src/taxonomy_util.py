import os

class TaxonomyUtil:
    
    def __init__(self, file_path):
        self.taxonomy_tree = self._load_taxonomy_file(file_path)
    
    def _load_taxonomy_file(self, file_path):
        taxonomy = {}
        current_class = None
        current_order = None
        current_family = None
        current_family_latin = None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.rstrip()
                if not stripped:
                    continue
                
                # Count leading tabs to determine hierarchy level
                level = len(line) - len(line.lstrip('\t'))
                content = stripped.strip()
                
                if level == 0:  # Class
                    current_class = content
                elif level == 1:  # Order
                    current_order = content.strip('[]')
                elif level == 2:  # Family
                    current_family = content.strip('[]')
                elif level == 3:  # Family Latin Name or Species
                    if content.startswith('{') and content.endswith('}'):
                        # Family Latin Name
                        current_family_latin = content.strip('{}')
                    else:
                        # Species
                        species = content
                        taxonomy[species] = {
                            'class': current_class,
                            'order': current_order,
                            'family': current_family,
                            'family_latin': current_family_latin,
                        }
                elif level == 4:  # Scientific name
                    # Update the last species entry with scientific name
                    if species in taxonomy:
                        taxonomy[species]['scientific_name'] = content.strip('{}')
        
        return taxonomy
    
    def _get_taxonomy(self, species_name):
        return self.taxonomy_tree.get(species_name, {})
    
    def parse_keywords_to_taxonomy(self, keywords):
        taxonomies = []
        for keyword in keywords:
            taxonomy = self.get_taxonomy(keyword)
            if taxonomy:
                taxonomies.append(taxonomy)
        return taxonomies

    def get_taxonomy(self, species_name):
        taxonomy = self._get_taxonomy(species_name)
        if taxonomy:
            return {
                'species': species_name,
                'class': taxonomy.get('class'),
                'order': taxonomy.get('order'),
                'family': taxonomy.get('family'),
                'family_latin': taxonomy.get('family_latin'),
                'scientific_name': taxonomy.get('scientific_name')
            }
        return {}
