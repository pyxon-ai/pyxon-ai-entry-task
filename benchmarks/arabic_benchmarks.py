"""
Advanced Arabic-Specific Benchmarks
Tests RTL handling, diacritics, encoding, and entity extraction
"""
import logging
from typing import Dict, List
import re

logger = logging.getLogger(__name__)


class ArabicBenchmarks:
    """Arabic-specific test suite"""
    
    def __init__(self):
        """Initialize Arabic benchmarks"""
        self.arabic_pattern = re.compile(r'[\u0600-\u06FF]')
        self.harakat_pattern = re.compile(r'[\u064B-\u065F]')
    
    def test_rtl_accuracy(self, processor, test_texts: List[str]) -> Dict:
        """
        Test RTL (Right-to-Left) text handling accuracy
        
        Args:
            processor: ArabicTextProcessor instance
            test_texts: List of test texts with known RTL issues
            
        Returns:
            Dictionary with RTL test results
        """
        logger.info("Testing RTL accuracy...")
        
        test_cases = [
            {
                'input': 'اذه ليلدلا',  # Reversed
                'expected': 'هذا الدليل',  # Correct
                'description': 'Simple word reversal'
            },
            {
                'input': 'ةداعإ ريودتلا',
                'expected': 'إعادة التدوير',
                'description': 'Complex word with hamza'
            }
        ]
        
        total_tests = len(test_cases)
        passed = 0
        
        results = []
        
        for test in test_cases:
            fixed = processor.fix_rtl_extraction(test['input'])
            is_correct = fixed.strip() == test['expected'].strip()
            
            if is_correct:
                passed += 1
            
            results.append({
                'input': test['input'],
                'expected': test['expected'],
                'output': fixed,
                'passed': is_correct,
                'description': test['description']
            })
        
        accuracy = passed / total_tests if total_tests > 0 else 0.0
        
        logger.info(f"RTL Accuracy: {accuracy:.2%} ({passed}/{total_tests} passed)")
        
        return {
            'accuracy': accuracy,
            'passed': passed,
            'total': total_tests,
            'details': results
        }
    
    def test_diacritics_preservation(self, processor, test_texts: List[str]) -> Dict:
        """
        Test diacritics (Harakat) preservation
        
        Args:
            processor: ArabicTextProcessor instance
            test_texts: List of texts with diacritics
            
        Returns:
            Dictionary with diacritics test results
        """
        logger.info("Testing diacritics preservation...")
        
        test_cases = [
            'الْحَمْدُ لِلَّهِ',
            'بِسْمِ اللَّهِ',
            'إِعَادَةُ التَّدْوِيرِ',
        ]
        
        preserved_count = 0
        total_diacritics = 0
        
        for text in test_cases:
            # Count original diacritics
            original_count = len(self.harakat_pattern.findall(text))
            
            # Process text
            processed = processor.process_text(text, mode='retrieval')
            retrieval_text = processed.get('retrieval', '')
            
            # Count preserved diacritics
            preserved = len(self.harakat_pattern.findall(retrieval_text))
            
            preserved_count += preserved
            total_diacritics += original_count
        
        preservation_rate = preserved_count / total_diacritics if total_diacritics > 0 else 0.0
        
        logger.info(f"Diacritics Preservation: {preservation_rate:.2%}")
        
        return {
            'preservation_rate': preservation_rate,
            'preserved': preserved_count,
            'total': total_diacritics
        }
    
    def test_encoding_handling(self, test_encodings: List[str] = None) -> Dict:
        """
        Test handling of different Arabic encodings
        
        Args:
            test_encodings: List of encodings to test
            
        Returns:
            Dictionary with encoding test results
        """
        if test_encodings is None:
            test_encodings = ['utf-8', 'utf-16', 'cp1256', 'iso-8859-6']
        
        logger.info(f"Testing {len(test_encodings)} encodings...")
        
        test_text = "هذا اختبار للترميز العربي"
        
        successful = 0
        results = []
        
        for encoding in test_encodings:
            try:
                # Encode and decode
                encoded = test_text.encode(encoding)
                decoded = encoded.decode(encoding)
                
                success = decoded == test_text
                if success:
                    successful += 1
                
                results.append({
                    'encoding': encoding,
                    'success': success,
                    'error': None
                })
            except Exception as e:
                results.append({
                    'encoding': encoding,
                    'success': False,
                    'error': str(e)
                })
        
        success_rate = successful / len(test_encodings) if test_encodings else 0.0
        
        logger.info(f"Encoding Success Rate: {success_rate:.2%}")
        
        return {
            'success_rate': success_rate,
            'successful': successful,
            'total': len(test_encodings),
            'details': results
        }
    
    def test_entity_extraction(self, processor, test_texts: List[str]) -> Dict:
        """
        Test Arabic named entity extraction
        
        Args:
            processor: ArabicTextProcessor instance
            test_texts: List of texts containing entities
            
        Returns:
            Dictionary with entity extraction results
        """
        logger.info("Testing entity extraction...")
        
        test_texts_with_entities = [
            {
                'text': 'شركة إعادة التدوير في عمان',
                'expected_entities': ['شركة إعادة التدوير'],
                'expected_count': 1
            },
            {
                'text': 'مركز البيئة في مدينة الزرقاء',
                'expected_entities': ['مركز البيئة', 'مدينة الزرقاء'],
                'expected_count': 2
            }
        ]
        
        total_expected = sum(t['expected_count'] for t in test_texts_with_entities)
        total_extracted = 0
        
        results = []
        
        for test in test_texts_with_entities:
            entities = processor.extract_arabic_entities(test['text'])
            total_extracted += len(entities)
            
            results.append({
                'text': test['text'],
                'expected': test['expected_count'],
                'extracted': len(entities),
                'entities': entities
            })
        
        extraction_rate = total_extracted / total_expected if total_expected > 0 else 0.0
        
        logger.info(f"Entity Extraction Rate: {extraction_rate:.2%}")
        
        return {
            'extraction_rate': extraction_rate,
            'total_extracted': total_extracted,
            'total_expected': total_expected,
            'details': results
        }
    
    def run_all_arabic_tests(self, processor) -> Dict:
        """
        Run all Arabic-specific tests
        
        Args:
            processor: ArabicTextProcessor instance
            
        Returns:
            Dictionary with all test results
        """
        logger.info("Running comprehensive Arabic tests...")
        
        # RTL test
        rtl_results = self.test_rtl_accuracy(processor, [])
        
        # Diacritics test
        diacritics_results = self.test_diacritics_preservation(processor, [])
        
        # Encoding test
        encoding_results = self.test_encoding_handling()
        
        # Entity extraction test
        entity_results = self.test_entity_extraction(processor, [])
        
        # Overall score
        overall_score = (
            rtl_results['accuracy'] * 0.3 +
            diacritics_results['preservation_rate'] * 0.3 +
            encoding_results['success_rate'] * 0.2 +
            entity_results['extraction_rate'] * 0.2
        )
        
        logger.info(f"Overall Arabic Test Score: {overall_score:.2%}")
        
        return {
            'overall_score': overall_score,
            'rtl': rtl_results,
            'diacritics': diacritics_results,
            'encoding': encoding_results,
            'entities': entity_results
        }
