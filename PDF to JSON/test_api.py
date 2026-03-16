"""
Test script for PDF to JSON API
Tests all endpoints with sample data
"""
import requests
import json
import sys
from pathlib import Path

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"


def test_health_check():
    """Test health check endpoint"""
    print("\n" + "=" * 60)
    print("TEST 1: Health Check")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Health check passed")
            return True
        else:
            print("❌ Health check failed")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_upload_pdf(pdf_path=None):
    """Test PDF upload endpoint"""
    print("\n" + "=" * 60)
    print("TEST 2: Upload PDF")
    print("=" * 60)
    
    if pdf_path is None:
        print("⚠️  No PDF file provided. Skipping upload test.")
        print("Usage: python test_api.py <path_to_pdf_file>")
        return None
    
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"❌ PDF file not found: {pdf_path}")
        return None
    
    try:
        with open(pdf_path, "rb") as f:
            files = {"file": (pdf_file.name, f, "application/pdf")}
            response = requests.post(f"{API_BASE}/upload-pdf", files=files)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201:
            request_id = response.json()["request_id"]
            print(f"✅ PDF uploaded successfully - ID: {request_id}")
            return request_id
        else:
            print("❌ PDF upload failed")
            return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None


def test_fulltext_extraction(request_id):
    """Test full text extraction endpoint"""
    print("\n" + "=" * 60)
    print("TEST 3: Full Text Extraction")
    print("=" * 60)
    
    if request_id is None:
        print("⚠️  Skipping - no valid request_id")
        return False
    
    try:
        response = requests.get(f"{API_BASE}/pdf/{request_id}/fulltext")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            full_text = data["full_text"]
            print(f"Request ID: {data['request_id']}")
            print(f"Text Length: {len(full_text)} characters")
            print(f"First 200 characters:\n{full_text[:200]}...")
            print("✅ Full text extraction successful")
            return True
        else:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            print("❌ Full text extraction failed")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_structured_extraction(request_id):
    """Test structured data extraction endpoint"""
    print("\n" + "=" * 60)
    print("TEST 4: Structured Data Extraction")
    print("=" * 60)
    
    if request_id is None:
        print("⚠️  Skipping - no valid request_id")
        return False
    
    try:
        response = requests.get(f"{API_BASE}/pdf/{request_id}/extract")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            extracted_data = data["data"]
            print(f"Request ID: {data['request_id']}")
            print(f"Extracted Fields ({len(extracted_data)}):")
            print(json.dumps(extracted_data, indent=2))
            print("✅ Structured extraction successful")
            return True
        else:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            print("❌ Structured extraction failed")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_invalid_request_id():
    """Test with invalid request_id"""
    print("\n" + "=" * 60)
    print("TEST 5: Invalid Request ID (Error Handling)")
    print("=" * 60)
    
    try:
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = requests.get(f"{API_BASE}/pdf/{fake_id}/fulltext")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 404:
            print("✅ Error handling works correctly")
            return True
        else:
            print("❌ Unexpected response")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("PDF to JSON API - Comprehensive Test Suite")
    print("=" * 60)
    print(f"API Base URL: {BASE_URL}")
    
    # Check if server is running
    try:
        requests.get(BASE_URL, timeout=2)
    except requests.exceptions.RequestException:
        print("\n❌ Error: API server is not running!")
        print("Please start the server first:")
        print("  python run.py")
        sys.exit(1)
    
    # Get PDF path from command line
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Run tests
    results = []
    
    # Test 1: Health Check
    results.append(("Health Check", test_health_check()))
    
    # Test 2-4: PDF Processing (if PDF provided)
    request_id = test_upload_pdf(pdf_path)
    if request_id:
        results.append(("PDF Upload", True))
        results.append(("Full Text Extraction", test_fulltext_extraction(request_id)))
        results.append(("Structured Extraction", test_structured_extraction(request_id)))
    else:
        if pdf_path:
            results.append(("PDF Upload", False))
    
    # Test 5: Error Handling
    results.append(("Error Handling", test_invalid_request_id()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:30} {status}")
    
    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 All tests passed successfully!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
