"""
Test script for RAW_HOPPER logic without GUI dependencies.
This tests the HopperLogic class functionality.
"""

import sys
import os
import tempfile
import json
from datetime import datetime

# Import only the logic parts - we'll handle tkinter error
sys.path.insert(0, os.path.dirname(__file__))

# Mock tkinter if not available
try:
    import tkinter
except ImportError:
    # Create a mock tkinter module
    class MockTk:
        pass

    class MockModule:
        Tk = MockTk
        StringVar = type
        Text = type
        Canvas = type
        Frame = type

        def __getattr__(self, name):
            return type(name, (), {})

    sys.modules['tkinter'] = MockModule()
    sys.modules['tkinter.ttk'] = MockModule()
    sys.modules['tkinter.filedialog'] = MockModule()
    sys.modules['tkinter.messagebox'] = MockModule()


def test_config_persistence():
    """Test configuration save and load."""
    print("Testing configuration persistence...")

    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json',
                                     delete=False) as f:
        config_path = f.name

    try:
        # Import after ensuring path
        from raw_hopper import HopperLogic

        # Create logic instance
        logic = HopperLogic(config_path)

        # Modify config
        logic.config['year_format'] = '%Y-TEST'
        logic.config['source_path'] = '/test/path'
        logic.save_config()

        # Create new instance and verify it loaded the saved config
        logic2 = HopperLogic(config_path)
        assert logic2.config['year_format'] == '%Y-TEST'
        assert logic2.config['source_path'] == '/test/path'

        print("✓ Configuration persistence test passed")
        return True
    finally:
        if os.path.exists(config_path):
            os.unlink(config_path)


def test_path_construction():
    """Test path construction from date."""
    print("Testing path construction...")

    from raw_hopper import HopperLogic

    logic = HopperLogic()

    # Test with a known date
    test_date = datetime(2024, 3, 15, 10, 30, 0)

    year, month, session = logic.construct_path(test_date)

    assert year == '2024', f"Expected '2024', got '{year}'"
    assert month == '2024-03_March', f"Expected '2024-03_March', got '{month}'"
    assert session == 'Session_March', (
        f"Expected 'Session_March', got '{session}'"
    )

    print("✓ Path construction test passed")
    return True


def test_file_extension_filter():
    """Test file extension filtering."""
    print("Testing file extension filtering...")

    from raw_hopper import HopperLogic

    logic = HopperLogic()
    logic.config['file_extensions'] = '.RAF, .JPG, .CR2'

    assert logic.should_process_file('photo.RAF')
    assert logic.should_process_file('photo.jpg')  # Case insensitive
    assert logic.should_process_file('photo.CR2')
    assert not logic.should_process_file('photo.txt')
    assert not logic.should_process_file('photo.mp4')

    print("✓ File extension filtering test passed")
    return True


def main():
    """Run all tests."""
    print("="*50)
    print("RAW_HOPPER Logic Tests")
    print("="*50)

    tests = [
        test_config_persistence,
        test_path_construction,
        test_file_extension_filter,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed: {e}")
            failed += 1

    print("="*50)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*50)

    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
