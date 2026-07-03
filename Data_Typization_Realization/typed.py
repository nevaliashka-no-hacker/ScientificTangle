import zipfile
import io
import json
from pathlib import Path
from datetime import datetime
from pypdf import PdfReader
from docx import Document
from pptx import Presentation
import tempfile
import os


class FullRecursiveZipProcessor:
    """
    Полная рекурсивная обработка ZIP-архивов с любой вложенностью.
    Поддерживает: PDF, DOCX, DOC, PPTX, ZIP (вложенные), TXT
    """
    
    def __init__(self):
        self.processed_count = 0
        self.error_count = 0
        
    def process_zip_file(self, zip_path: str, output_file: str = "documents.json"):
        """
        Главный метод - обработка ZIP файла
        
        Args:
            zip_path: Путь к ZIP файлу
            output_file: Имя выходного JSON файла
        """
        print(f"🚀 Начинаю обработку: {zip_path}")
        print("=" * 60)
        
        # Считываем весь ZIP в память
        with open(zip_path, 'rb') as f:
            zip_data = f.read()
        
        # Запускаем рекурсивную обработку
        documents = self._process_zip_data(
            zip_data=zip_data,
            archive_name=Path(zip_path).stem,
            parent_path=""
        )
        
        # Сохраняем результат
        self._save_to_json(documents, output_file)
        
        # Выводим статистику
        self._print_final_stats(documents)
        
        return documents
    
    def _process_zip_data(self, zip_data: bytes, archive_name: str, parent_path: str) -> list:
        """
        Рекурсивная обработка ZIP данных
        
        Args:
            zip_data: Бинарные данные ZIP архива
            archive_name: Имя текущего архива
            parent_path: Родительский путь (для сохранения структуры папок)
        
        Returns:
            Список обработанных документов
        """
        documents = []
        
        try:
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zip_ref:
                all_items = zip_ref.infolist()
                
                folder_structure = self._get_folder_structure(all_items)
                
                print(f"\n📂 Архив: {archive_name}")
                print(f"   Папок: {len(folder_structure)}")
                print(f"   Файлов: {len([f for f in all_items if not f.is_dir()])}")
                
                for file_info in all_items:
                    if file_info.is_dir():
                        continue 
                    
                    if parent_path:
                        full_path = f"{parent_path}/{archive_name}/{file_info.filename}"
                    else:
                        full_path = f"{archive_name}/{file_info.filename}"
                    
                    full_path = full_path.replace('//', '/')
                    
                    ext = Path(file_info.filename).suffix.lower()
                    
                    print(f"⚙️  Обрабатываю: {full_path}")
                    
                    try:
                        file_data = zip_ref.read(file_info)
                        
                        if ext == '.zip':
                            print(f"   📦 Обнаружен вложенный архив!")
                            nested_docs = self._process_zip_data(
                                zip_data=file_data,
                                archive_name=Path(file_info.filename).stem,
                                parent_path=full_path.replace(f'/{file_info.filename}', '')
                            )
                            documents.extend(nested_docs)
                            
                            documents.append(self._get_zip_info(file_data, full_path))
                            
                        elif ext == '.pdf':
                            doc = self._process_pdf(file_data, full_path)
                            documents.append(doc)
                            self.processed_count += 1
                            
                        elif ext in ['.docx', '.doc']:
                            doc = self._process_docx(file_data, full_path)
                            documents.append(doc)
                            self.processed_count += 1
                            
                        elif ext == '.pptx':
                            doc = self._process_pptx(file_data, full_path)
                            documents.append(doc)
                            self.processed_count += 1
                            
                        elif ext in ['.txt', '.md', '.csv', '.json', '.xml', '.html']:
                            doc = self._process_text_file(file_data, full_path)
                            documents.append(doc)
                            self.processed_count += 1
                            
                        else:
                            documents.append({
                                "название": full_path,
                                "содержание": f"Неподдерживаемый формат: {ext}",
                                "тип_файла": ext,
                                "статус": "unsupported"
                            })
                            print(f"   ⚠️  Пропущен (неподдерживаемый формат)")
                        
                    except Exception as e:
                        print(f"   ❌ Ошибка: {e}")
                        documents.append({
                            "название": full_path,
                            "содержание": f"ОШИБКА ОБРАБОТКИ: {str(e)}",
                            "тип_файла": ext,
                            "статус": "error"
                        })
                        self.error_count += 1
                
        except zipfile.BadZipFile:
            print(f"❌ Файл не является ZIP архивом: {archive_name}")
            documents.append({
                "название": archive_name,
                "содержание": "Ошибка: файл не является ZIP архивом",
                "тип_файла": ".zip",
                "статус": "error"
            })
            self.error_count += 1
        
        return documents
    
    def _get_folder_structure(self, items: list) -> dict:
        folders = {}
        for item in items:
            if item.is_dir():
                path = item.filename.rstrip('/')
                folders[path] = []
        return folders
    
    def _get_zip_info(self, zip_data: bytes, file_path: str) -> dict:
        try:
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                file_list = [f.filename for f in zf.infolist() if not f.is_dir()]
                
                total_size = sum(f.file_size for f in zf.infolist())
                
                return {
                    "название": file_path,
                    "содержание": f"ZIP архив ({len(file_list)} файлов, {total_size / 1024:.1f} КБ):\n" + 
                                 "\n".join(f"  • {f}" for f in file_list[:50]) +  
                                 ("\n  ... и еще файлы" if len(file_list) > 50 else ""),
                    "тип_файла": ".zip",
                    "количество_файлов_в_архиве": len(file_list),
                    "размер_архива_КБ": round(total_size / 1024, 1),
                    "список_файлов": file_list[:100],  
                    "статус": "success"
                }
        except Exception as e:
            return {
                "название": file_path,
                "содержание": f"Ошибка чтения ZIP: {str(e)}",
                "тип_файла": ".zip",
                "статус": "error"
            }
    
    def _process_pdf(self, file_data: bytes, file_path: str) -> dict:
        pdf_file = io.BytesIO(file_data)
        reader = PdfReader(pdf_file)
        
        text_parts = []
        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            if text and text.strip():
                text_parts.append(f"[Страница {page_num}]\n{text}")
        
        content = "\n\n".join(text_parts) if text_parts else "PDF без текстового слоя"
        
        print(f"   ✅ PDF: {len(reader.pages)} стр.")
        
        return {
            "название": file_path,
            "содержание": content,
            "тип_файла": ".pdf",
            "количество_страниц": len(reader.pages),
            "статус": "success"
        }
    
    def _process_docx(self, file_data: bytes, file_path: str) -> dict:
        doc_file = io.BytesIO(file_data)
        doc = Document(doc_file)
        
        text_parts = []
        
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        
        tables_count = len(doc.tables)
        for table_num, table in enumerate(doc.tables, 1):
            text_parts.append(f"\n[Таблица {table_num}]")
            for row in table.rows:
                row_data = [cell.text for cell in row.cells]
                text_parts.append(" | ".join(row_data))
        
        content = "\n".join(text_parts) if text_parts else "Документ без текста"
        
        print(f"   ✅ DOCX: {len(doc.paragraphs)} параграфов, {tables_count} таблиц")
        
        return {
            "название": file_path,
            "содержание": content,
            "тип_файла": Path(file_path).suffix.lower(),
            "количество_параграфов": len(doc.paragraphs),
            "количество_таблиц": tables_count,
            "статус": "success"
        }
    
    def _process_pptx(self, file_data: bytes, file_path: str) -> dict:
        pptx_file = io.BytesIO(file_data)
        prs = Presentation(pptx_file)
        
        text_parts = []
        for slide_num, slide in enumerate(prs.slides, 1):
            slide_text = [f"[Слайд {slide_num}]"]
            
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_text.append(shape.text)
                
                if shape.has_table:
                    table_text = ["\nТаблица:"]
                    for row in shape.table.rows:
                        row_data = [cell.text for cell in row.cells]
                        table_text.append(" | ".join(row_data))
                    slide_text.extend(table_text)
            
            text_parts.append("\n".join(slide_text))
        
        content = "\n\n".join(text_parts) if text_parts else "Презентация без текста"
        
        print(f"   ✅ PPTX: {len(prs.slides)} слайдов")
        
        return {
            "название": file_path,
            "содержание": content,
            "тип_файла": ".pptx",
            "количество_слайдов": len(prs.slides),
            "статус": "success"
        }
    
    def _process_text_file(self, file_data: bytes, file_path: str) -> dict:
        """Обработка текстовых файлов"""
        for encoding in ['utf-8', 'cp1251', 'latin-1']:
            try:
                text = file_data.decode(encoding)
                break
            except:
                continue
        else:
            text = file_data.decode('utf-8', errors='ignore')
        
        ext = Path(file_path).suffix.lower()
        
        print(f"   ✅ {ext.upper()}: {len(text)} символов")
        
        return {
            "название": file_path,
            "содержание": text,
            "тип_файла": ext,
            "размер_символов": len(text),
            "статус": "success"
        }
    
    def _save_to_json(self, documents: list, output_file: str):
        """Сохранение результатов в JSON"""
        output_data = {
            "метаданные": {
                "дата_обработки": datetime.now().isoformat(),
                "общее_количество_документов": len(documents),
                "успешно_обработано": self.processed_count,
                "с_ошибками": self.error_count,
                "статистика_по_типам": self._get_stats(documents)
            },
            "документы": documents
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Результат сохранен в: {output_file}")
    
    def _get_stats(self, documents: list) -> dict:
        """Подсчет статистики"""
        stats = {}
        for doc in documents:
            doc_type = doc.get("тип_файла", "неизвестный")
            status = doc.get("статус", "unknown")
            
            if doc_type not in stats:
                stats[doc_type] = {"всего": 0, "успешно": 0, "с_ошибками": 0}
            
            stats[doc_type]["всего"] += 1
            if status == "success":
                stats[doc_type]["успешно"] += 1
            else:
                stats[doc_type]["с_ошибками"] += 1
        
        return stats
    
    def _print_final_stats(self, documents: list):
        """Вывод финальной статистики"""
        print("\n" + "=" * 60)
        print("📊 ФИНАЛЬНАЯ СТАТИСТИКА")
        print("=" * 60)
        
        stats = self._get_stats(documents)
        for file_type, stat in sorted(stats.items()):
            print(f"  {file_type}: {stat['всего']} всего "
                  f"({stat['успешно']} успешно, {stat['с_ошибками']} с ошибками)")
        
        print(f"\n  ✅ Всего успешно: {self.processed_count}")
        print(f"  ❌ Всего ошибок: {self.error_count}")
        print(f"  📁 Всего записей: {len(documents)}")

# ============================================

if __name__ == "__main__":

    ZIP_FILE_PATH = r"C:\Users\Username\Downloads\archive.zip" 
    
    processor = FullRecursiveZipProcessor()
    
    try:
        documents = processor.process_zip_file(
            zip_path=ZIP_FILE_PATH,
            output_file="documents.json"
        )
        

        print("\n📋 ПРИМЕРЫ ДОКУМЕНТОВ:")
        for doc in documents[:5]:
            print(f"\n  📄 {doc['название']}")
            print(f"  Тип: {doc['тип_файла']} | Статус: {doc['статус']}")
            preview = doc['содержание'][:200].replace('\n', ' ')
            print(f"  {preview}...")
            
    except FileNotFoundError:
        print(f"❌ Файл не найден: {ZIP_FILE_PATH}")
        print("\nУкажите правильный путь к ZIP файлу")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()