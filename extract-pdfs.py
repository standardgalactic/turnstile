#!/usr/bin/env python3

import os
import sys
import glob
import argparse
import fitz  # PyMuPDF
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from email import policy
from email.parser import BytesParser

def extract_text_from_mhtml(file_path):
    with open(file_path, 'rb') as f:
        msg = BytesParser(policy=policy.default).parse(f)

    text_parts = []

    def decode_part(part):
        charset = part.get_content_charset() or 'utf-8'
        try:
            return part.get_payload(decode=True).decode(charset, errors='replace')
        except Exception as e:
            print(f"Warning: failed to decode part in {file_path}: {e}")
            return ''

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == 'text/html':
                html = decode_part(part)
                soup = BeautifulSoup(html, 'html.parser')
                text_parts.append(soup.get_text(separator="\n", strip=True))
            elif ctype == 'text/plain':
                text_parts.append(decode_part(part))
    else:
        ctype = msg.get_content_type()
        content = decode_part(msg)
        if ctype == 'text/html':
            soup = BeautifulSoup(content, 'html.parser')
            text_parts.append(soup.get_text(separator="\n", strip=True))
        else:
            text_parts.append(content)

    return "\n\n".join(text_parts)

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text("text") + "\n"
    except Exception as e:
        print(f"Error extracting PDF {pdf_path}: {e}")
    return text

def extract_text_from_epub(epub_path):
    text = ""
    try:
        book = epub.read_epub(epub_path)
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), "html.parser")
                text += soup.get_text() + "\n"
    except Exception as e:
        print(f"Error extracting EPUB {epub_path}: {e}")
    return text

def save_text(text, source_path):
    output_file = os.path.splitext(source_path)[0] + ".txt"
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Extracted text saved to: {output_file}")
    except Exception as e:
        print(f"Error saving {output_file}: {e}")

def process_file(file_path, parse_no_ext=False):
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        return

    file_lower = file_path.lower()

    if file_lower.endswith(".pdf"):
        print(f"Processing PDF: {file_path}")
        text = extract_text_from_pdf(file_path)
    elif file_lower.endswith(".epub"):
        print(f"Processing EPUB: {file_path}")
        text = extract_text_from_epub(file_path)
    elif file_lower.endswith((".mhtml", ".mht")) or (parse_no_ext and not os.path.splitext(file_lower)[1]):
        print(f"Processing MHTML: {file_path}")
        text = extract_text_from_mhtml(file_path)
    else:
        print(f"Unsupported file type: {file_path}")
        return

    if text.strip():
        save_text(text, file_path)
    else:
        print(f"Warning: No text extracted from {file_path}")

def process_directory(directory, parse_no_ext=False):
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if filename.lower().endswith((".pdf", ".epub", ".mhtml", ".mht")) or (parse_no_ext and not os.path.splitext(filename)[1]):
            process_file(file_path, parse_no_ext=parse_no_ext)

def expand_wildcard_args(args):
    expanded = []
    for arg in args:
        if '*' in arg or '?' in arg:
            expanded.extend(glob.glob(arg))
        else:
            expanded.append(arg)
    return expanded

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract text from documents.")
    parser.add_argument("files", nargs='*', help="Files to process (wildcards allowed).")
    parser.add_argument("-p", "--parse", action="store_true", help="Treat files without extension as .mhtml")

    args = parser.parse_args()

    if args.files:
        files = expand_wildcard_args(args.files)
        for file in files:
            process_file(file, parse_no_ext=args.parse)
    else:
        print("No input files specified. Processing current directory.")
        process_directory(os.getcwd(), parse_no_ext=args.parse)
