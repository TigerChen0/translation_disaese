#!/usr/bin/env python3
# ==============================================================================
#  Batch Translation System for Disease Terms
#  Using DeepSeek LLM 7B for Traditional Chinese Medicine Translation
#  Processes all xlsx files in current directory
# ==============================================================================

import os
import gc
import re
import json
import pandas as pd
import torch
import yaml
from transformers import AutoTokenizer, AutoModelForCausalLM
from datetime import datetime
import logging
import logging.handlers
import traceback
from pathlib import Path
from glob import glob

# 設定 Hugging Face 快取目錄到當前目錄
cache_dir = os.path.join(os.getcwd(), 'huggingface_cache')
os.makedirs(cache_dir, exist_ok=True)
os.environ['HF_HOME'] = cache_dir
os.environ['TRANSFORMERS_CACHE'] = cache_dir

class DiseaseTranslationBatch:
    def __init__(self, config_path='config.yaml'):
        # Load configuration first
        self.load_config(config_path)

        # Setup logging with config
        self.setup_logging()
        self.logger.info("=== Disease Translation Batch Processing Starting ===")

        # Initialize model and tokenizer
        self.load_model()

        # Load control data
        self.load_control_data()

    def load_config(self, config_path):
        """Load configuration from YAML file - exit if not found"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            print(f"Configuration loaded from: {config_path}")
        except FileNotFoundError:
            print(f"❌ Error: Config file '{config_path}' not found.")
            print(f"Please ensure config.yaml exists in the current directory.")
            print(f"Server cannot start without configuration file.")
            exit(1)
        except yaml.YAMLError as e:
            print(f"❌ Error: Invalid YAML syntax in '{config_path}': {e}")
            print(f"Please check the configuration file format.")
            exit(1)
        except Exception as e:
            print(f"❌ Error loading config file '{config_path}': {e}")
            exit(1)


    def setup_logging(self):
        """Setup rotating file logging system using config"""
        log_config = self.config['logging']['server']

        self.logger = logging.getLogger('DiseaseServer')
        self.logger.setLevel(getattr(logging, log_config['level'].upper()))

        # Clear any existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Create rotating file handler
        rh = logging.handlers.RotatingFileHandler(
            log_config['file'],
            maxBytes=log_config['max_size_mb'] * 1024 * 1024,
            backupCount=log_config['backup_count'],
            encoding='utf-8'
        )
        rh.setFormatter(logging.Formatter(log_config['format']))
        self.logger.addHandler(rh)

        # Also log to console
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter(log_config['format']))
        self.logger.addHandler(ch)

    def load_model(self):
        """Load the model using config - exit if model path doesn't exist"""
        try:
            model_config = self.config['model']
            system_config = self.config['system']

            # Get model path from config
            model_path = model_config['path']

            # Validate model path exists
            if model_path.startswith('/'):
                # Local path specified - must exist
                if not os.path.exists(model_path):
                    error_msg = f"Model path '{model_path}' specified in config.yaml does not exist."
                    print(f"❌ Error: {error_msg}")
                    print(f"Please ensure the model path in config.yaml is correct.")
                    raise FileNotFoundError(error_msg)
                self.logger.info(f"Loading model from local path: {model_path}")
            else:
                # HuggingFace path - will be downloaded if needed
                self.logger.info(f"Loading model from HuggingFace: {model_path}")

            # Set CUDA allocation config
            os.environ["PYTORCH_CUDA_ALLOC_CONF"] = system_config['cuda_alloc_conf']

            if not torch.cuda.is_available():
                self.logger.error("CUDA not available. This program requires NVIDIA GPU.")
                raise RuntimeError("CUDA not available")

            self.tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                trust_remote_code=model_config['trust_remote_code']
            )
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=model_config['torch_dtype'],
                device_map=model_config['device_map'],
                low_cpu_mem_usage=model_config['low_cpu_mem_usage'],
                trust_remote_code=model_config['trust_remote_code']
            )

            self.logger.info("Model and tokenizer loaded successfully to GPU!")

        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            self.logger.error(traceback.format_exc())
            raise

    def load_control_data(self):
        """Load control file data for context paragraphs using config"""
        try:
            control_file = self.config['files']['control_file']
            self.logger.info(f"Loading control file: {control_file}")
            self.control_df = pd.read_excel(control_file)

            if 'no' not in self.control_df.columns or 'disease_content' not in self.control_df.columns:
                raise ValueError("Control file missing required columns: 'no' or 'disease_content'")

            self.logger.info(f"Control data loaded successfully. Records: {len(self.control_df)}")

        except Exception as e:
            self.logger.error(f"Failed to load control file: {e}")
            raise

    def truncate_context_if_needed(self, context_paragraph: str, term: str) -> str:
        """Truncate context paragraph if the total prompt would exceed token limits"""
        translation_config = self.config['translation']
        max_tokens = translation_config['max_context_tokens']

        # Calculate base prompt tokens (without context) using template
        base_prompt = translation_config['prompt_template'].format(
            context_paragraph="",
            term=term
        )

        base_tokens = len(self.tokenizer.encode(base_prompt))
        available_tokens = max_tokens - base_tokens

        # If context is short enough, return as is
        context_tokens = len(self.tokenizer.encode(context_paragraph))
        if context_tokens <= available_tokens:
            return context_paragraph

        # Truncate context to fit within token limit
        self.logger.warning(f"Context too long ({context_tokens} tokens), truncating to {available_tokens} tokens")

        # Encode context and truncate
        context_token_ids = self.tokenizer.encode(context_paragraph)
        truncated_token_ids = context_token_ids[:available_tokens]
        truncated_context = self.tokenizer.decode(truncated_token_ids, skip_special_tokens=True)

        return truncated_context

    def find_classified_section_files(self):
        """Find all classified_section_*.xlsx files in current directory"""
        files_config = self.config['files']
        folder_path = files_config['folder_path']

        # Search for files matching pattern: classified_section_卷*.xlsx
        pattern = os.path.join(folder_path, 'classified_section_卷*.xlsx')
        matched_files = glob(pattern)

        # Extract just the filenames
        filenames = [os.path.basename(f) for f in matched_files]

        self.logger.info(f"Found {len(filenames)} classified_section files: {filenames}")
        return filenames

    def process_all_files(self):
        """Process all classified_section files - supports multiple files with single merged output"""
        try:
            # Find all xlsx files matching pattern
            filenames = self.find_classified_section_files()

            if not filenames:
                self.logger.warning("No classified_section files found to process")
                return

            self.logger.info(f"Starting batch processing for {len(filenames)} file(s): {', '.join(filenames)}")

            # Collect all translation results across all files
            all_translation_results = []
            volume_numbers = []
            files_processed = []
            error_count = 0
            warning_count = 0

            # Process each file sequentially
            for i, filename in enumerate(filenames, 1):
                self.logger.info(f"Processing file {i}/{len(filenames)}: {filename}")
                result = self.process_file_translation_for_merge(filename)

                if result['status'] == 'success' or result['status'] == 'warning':
                    all_translation_results.extend(result['translation_results'])
                    volume_numbers.append(result['volume_no'])
                    files_processed.append(filename)
                    if result['status'] == 'warning':
                        warning_count += 1
                else:
                    error_count += 1
                    self.logger.error(f"Failed to process file {filename}: {result.get('message', 'Unknown error')}")

            # Generate single merged output file if we have any results
            if all_translation_results:
                self.generate_merged_output(all_translation_results, volume_numbers, files_processed)

            # Determine overall status
            success_count = len(files_processed) - warning_count
            if error_count == 0 and warning_count == 0:
                overall_status = 'success'
            elif error_count == 0:
                overall_status = 'warning'
            else:
                overall_status = 'partial_success' if success_count > 0 else 'error'

            # Print summary
            self.logger.info(f"Batch processing completed: {overall_status}")
            self.logger.info(f"Total files: {len(filenames)}, Success: {success_count}, Warning: {warning_count}, Error: {error_count}")
            self.logger.info(f"Total translations: {len(all_translation_results)}")

        except Exception as e:
            self.logger.error(f"Batch processing failed: {e}")
            self.logger.error(traceback.format_exc())

    def execute_translation_prompt(self, full_prompt: str) -> str:
        """Execute translation using the local model with config"""
        try:
            generation_config = self.config['model']['generation']
            translation_config = self.config['translation']

            messages = [{'role': 'user', 'content': full_prompt}]
            input_ids = self.tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt")

            # Check if sequence is too long
            sequence_length = input_ids.shape[-1]
            max_seq_length = translation_config['max_sequence_length']
            if sequence_length > max_seq_length:
                self.logger.warning(f"Input sequence length ({sequence_length}) exceeds model limit ({max_seq_length}). This may cause errors.")

            attention_mask = torch.ones_like(input_ids)

            outputs = self.model.generate(
                input_ids.to(self.model.device),
                attention_mask=attention_mask.to(self.model.device),
                max_new_tokens=generation_config['max_new_tokens'],
                do_sample=generation_config['do_sample'],
                temperature=generation_config['temperature'],
                top_p=generation_config['top_p'],
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.eos_token_id
            )

            response = self.tokenizer.decode(outputs[0][input_ids.shape[-1]:], skip_special_tokens=True)

            # Memory cleanup if configured
            if self.config['system']['memory_cleanup']:
                gc.collect()
                torch.cuda.empty_cache()

            return response.strip()

        except Exception as e:
            self.logger.error(f"Translation error: {e}")
            return f"翻譯失敗：模型處理錯誤 - {str(e)}"

    def _process_file_core_translation(self, filename: str, volume_no: int, target_df) -> dict:
        """Core translation logic shared between different processing modes"""
        try:
            # Get all terms and their corresponding sections
            valid_rows = target_df[target_df['disease'].notna() & target_df['section'].notna()]
            self.logger.info(f"Found {len(valid_rows)} valid term-section pairs to translate")

            # Perform translations
            translation_results = []
            fallback_used = False
            actual_volume_used = volume_no  # Initialize with original volume number

            # Track fallback usage statistics
            fallback_level1_count = 0  # Same volume, different section
            fallback_level2_count = 0  # Different volume (nearest)

            for index, row in valid_rows.iterrows():
                term = row['disease']
                section = row['section']

                # Remove leading "治療" or "治" characters if present
                if term and str(term).startswith('治療'):
                    term = str(term)[2:]  # Remove the first two characters
                    self.logger.debug(f"Removed leading '治療' from term, new term: '{term}'")
                elif term and str(term).startswith('治'):
                    term = str(term)[1:]  # Remove the first character
                    self.logger.debug(f"Removed leading '治' from term, new term: '{term}'")

                if not str(term).strip() or not str(section).strip():
                    continue

                self.logger.debug(f"Translating term: '{term}' with section: '{section}'")

                # Find corresponding context paragraph using both no and section
                context_row = self.control_df[
                    (self.control_df['no'] == volume_no) &
                    (self.control_df['section'] == section)
                ]

                context_paragraph = None
                actual_section_used = section

                if context_row.empty:
                    # Try fallback: find any row with same volume number
                    volume_fallback = self.control_df[self.control_df['no'] == volume_no]
                    if not volume_fallback.empty:
                        context_row = volume_fallback.iloc[[0]]  # Take first available
                        actual_section_used = context_row.iloc[0]['section']
                        fallback_used = True
                        fallback_level1_count += 1
                        self.logger.warning(f"⚠️ FALLBACK LEVEL 1: No exact match for volume {volume_no} + section '{section}', using same volume with section '{actual_section_used}' as fallback")
                    else:
                        # Ultimate fallback: find nearest volume
                        available_volumes = sorted(self.control_df['no'].unique())
                        nearest_volume = min(available_volumes, key=lambda x: abs(x - volume_no))
                        nearest_fallback = self.control_df[self.control_df['no'] == nearest_volume]
                        if not nearest_fallback.empty:
                            context_row = nearest_fallback.iloc[[0]]
                            actual_section_used = context_row.iloc[0]['section']
                            actual_volume_used = nearest_volume  # Set the actual volume used for fallback
                            fallback_used = True
                            fallback_level2_count += 1
                            self.logger.warning(f"⚠️ FALLBACK LEVEL 2: No context found for volume {volume_no}, using nearest volume {nearest_volume} + section '{actual_section_used}' as fallback")
                        else:
                            self.logger.error(f"No context found for term '{term}' with section '{section}'")
                            continue

                context_paragraph = context_row.iloc[0]['disease_content']
                if pd.isna(context_paragraph):
                    self.logger.warning(f"Context paragraph is empty for volume {volume_no} + section '{actual_section_used}', skipping term '{term}'")
                    continue

                # Truncate context if needed to avoid token limit
                truncated_context = self.truncate_context_if_needed(context_paragraph, term)

                # Use prompt template from config
                full_prompt = self.config['translation']['prompt_template'].format(
                    context_paragraph=truncated_context,
                    term=term
                )

                # Execute translation
                translated_text = self.execute_translation_prompt(full_prompt)
                self.logger.info(f"翻譯結果: '{translated_text}'")

                # Store results
                translation_results.append({
                    '卷號': volume_no,
                    '章節': section,
                    '原始文本': term,
                    '翻譯結果': translated_text
                })

            # Log fallback usage summary
            if fallback_level1_count > 0 or fallback_level2_count > 0:
                self.logger.warning(f"📊 FALLBACK SUMMARY for {filename}: Level 1 (same volume): {fallback_level1_count}, Level 2 (different volume): {fallback_level2_count}")

            return {
                'translation_results': translation_results,
                'fallback_used': fallback_used,
                'actual_volume_used': actual_volume_used,
                'fallback_level1_count': fallback_level1_count,
                'fallback_level2_count': fallback_level2_count
            }

        except Exception as e:
            self.logger.error(f"Core translation error for {filename}: {e}")
            self.logger.error(traceback.format_exc())
            raise

    def process_file_translation_for_merge(self, filename: str) -> dict:
        """Process translation for a specific file - returns translation results for merging"""
        try:
            self.logger.info(f"Processing file for merge: {filename}")

            # Extract volume number from filename using config regex
            files_config = self.config['files']
            match = re.search(files_config['volume_regex'], filename)
            if not match:
                raise ValueError(f"Cannot extract volume number from filename: {filename}")

            volume_no = int(match.group(1))
            self.logger.info(f"Extracted volume number: {volume_no}")

            # Load target file first to get section information
            file_path = os.path.join(files_config['folder_path'], filename)
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Target file not found: {file_path}")

            target_df = pd.read_excel(file_path)
            if 'disease' not in target_df.columns:
                raise ValueError(f"Column 'disease' not found in file: {filename}")
            if 'section' not in target_df.columns:
                raise ValueError(f"Column 'section' not found in file: {filename}")

            # Use core translation logic
            core_result = self._process_file_core_translation(filename, volume_no, target_df)

            # Extract results
            translation_results = core_result['translation_results']
            fallback_used = core_result['fallback_used']
            actual_volume_used = core_result['actual_volume_used']

            # Return results for merging instead of generating individual file
            status = 'success'
            message = f'Translation completed successfully for {len(translation_results)} terms'

            if fallback_used:
                status = 'warning'
                message = f'Translation completed for {len(translation_results)} terms (used volume {actual_volume_used} context as fallback)'

            return {
                'status': status,
                'message': message,
                'volume_no': volume_no,
                'translation_results': translation_results,
                'fallback_used': fallback_used,
                'actual_volume_used': actual_volume_used if fallback_used else volume_no
            }

        except Exception as e:
            self.logger.error(f"Error processing file {filename}: {e}")
            self.logger.error(traceback.format_exc())
            return {
                'status': 'error',
                'message': f'Translation failed: {str(e)}',
                'filename': filename,
                'translation_results': []
            }

    def generate_merged_output(self, all_translation_results, volume_numbers, files_processed):
        """Generate single merged output file for all translations"""
        try:
            files_config = self.config['files']

            # Create DataFrame from all results
            results_df = pd.DataFrame(all_translation_results)

            # Generate output filename
            today_str = datetime.now().strftime(files_config['output']['date_format'])

            if len(volume_numbers) == 1:
                # Single file case
                output_filename = files_config['output']['single_format'].format(
                    vol=volume_numbers[0],
                    date=today_str
                )
            else:
                # Multiple files case - use batch format
                min_vol = min(volume_numbers)
                max_vol = max(volume_numbers)
                output_filename = files_config['output']['batch_format'].format(
                    min_vol=min_vol,
                    max_vol=max_vol,
                    date=today_str
                )

            output_path = os.path.join(files_config['folder_path'], output_filename)
            results_df.to_excel(output_path, index=False)

            self.logger.info(f"Merged translation report saved: {output_path}")
            self.logger.info(f"Total translations: {len(all_translation_results)} from {len(files_processed)} files")

        except Exception as e:
            self.logger.error(f"Error generating merged output: {e}")
            self.logger.error(traceback.format_exc())

    def process_file_translation(self, filename: str) -> dict:
        """Process translation for a specific file"""
        try:
            self.logger.info(f"Processing file: {filename}")

            # Extract volume number from filename using config regex
            files_config = self.config['files']
            match = re.search(files_config['volume_regex'], filename)
            if not match:
                raise ValueError(f"Cannot extract volume number from filename: {filename}")

            volume_no = int(match.group(1))
            self.logger.info(f"Extracted volume number: {volume_no}")

            # Load target file first to get section information
            file_path = os.path.join(files_config['folder_path'], filename)
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Target file not found: {file_path}")

            target_df = pd.read_excel(file_path)
            if 'disease' not in target_df.columns:
                raise ValueError(f"Column 'disease' not found in file: {filename}")
            if 'section' not in target_df.columns:
                raise ValueError(f"Column 'section' not found in file: {filename}")

            # Use core translation logic
            core_result = self._process_file_core_translation(filename, volume_no, target_df)

            # Extract results
            translation_results = core_result['translation_results']
            fallback_used = core_result['fallback_used']
            actual_volume_used = core_result['actual_volume_used']

            if translation_results:
                # Create DataFrame for output
                results_df = pd.DataFrame(translation_results)

                # Generate output filename using config
                today_str = datetime.now().strftime(files_config['output']['date_format'])
                output_filename = files_config['output']['single_format'].format(
                    vol=volume_no,
                    date=today_str
                )

                output_path = os.path.join(files_config['folder_path'], output_filename)
                results_df.to_excel(output_path, index=False)
                self.logger.info(f"Translation report saved: {output_path}")

                # Check if we used a fallback context
                status = 'success'
                message = f'Translation completed successfully for {len(translation_results)} terms'
                extra_info = {}

                # Check if we used fallback context
                if fallback_used:
                    status = 'warning'
                    message = f'Translation completed for {len(translation_results)} terms (used volume {actual_volume_used} context as fallback)'
                    extra_info['fallback_context_volume'] = actual_volume_used

                result = {
                    'status': status,
                    'message': message,
                    'volume_no': volume_no,
                    'translated_terms': len(translation_results),
                    'output_file': output_filename
                }
                result.update(extra_info)
                return result

            else:
                return {
                    'status': 'warning',
                    'message': 'No terms found to translate',
                    'volume_no': volume_no,
                    'translated_terms': 0,
                    'output_file': None
                }

        except Exception as e:
            self.logger.error(f"Error processing file {filename}: {e}")
            self.logger.error(traceback.format_exc())
            return {
                'status': 'error',
                'message': f'Translation failed: {str(e)}',
                'filename': filename,
                'volume_no': None,
                'translated_terms': 0,
                'output_file': None
            }


def main():
    """Main function"""
    batch_processor = None
    try:
        batch_processor = DiseaseTranslationBatch()
        batch_processor.process_all_files()
        print("\n✅ Batch processing completed. Check logs for details.")
    except KeyboardInterrupt:
        print("\n⚠️ Processing interrupted by user")
        if batch_processor:
            batch_processor.logger.info("Processing interrupted by user")
    except Exception as e:
        print(f"❌ Processing error: {e}")
        if batch_processor:
            batch_processor.logger.error(f"Fatal processing error: {e}")
            batch_processor.logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()