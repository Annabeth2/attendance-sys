import asyncio
from bleak import BleakScanner
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Set, Optional
import logging
from models import User, Enrollment, Attendance, UserRole, AttendanceType
from database import SessionLocal
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BluetoothScanner:
    def __init__(self, db: Optional[Session] = None):
        self.detected_devices: Dict[str, datetime] = {}
        self.scanning = False
        self.db = db or SessionLocal()
        self.cleanup_task: Optional[asyncio.Task] = None
        self.scanner: Optional[BleakScanner] = None
        self.last_error: Optional[str] = None
        self.active_broadcast = None  # Store active broadcast info
        logger.info("BluetoothScanner initialized")

    async def device_detection_callback(self, device, advertisement_data):
        """Callback function for when a device is detected"""
        try:
            if not hasattr(device, 'address'):
                logger.warning(f"Invalid device detected: {device}")
                return
                
            address = device.address
            logger.debug(f"Device detected: {address}")
            
            if address in self.detected_devices:
                # Update last seen time
                self.detected_devices[address] = datetime.utcnow()
                logger.debug(f"Updated last seen time for device: {address}")
            else:
                # New device detected
                self.detected_devices[address] = datetime.utcnow()
                logger.info(f"New device detected: {address}")
                await self.process_device(address)
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error in device detection callback: {str(e)}")
            logger.error(traceback.format_exc())

    async def process_device(self, address: str):
        """Process a detected device and update attendance if it matches a student"""
        try:
            logger.info(f"Processing device: {address}")
            
            # Query database for student with matching Bluetooth address
            student = self.db.query(User).filter(
                User.bluetooth_address == address,
                User.role == UserRole.STUDENT
            ).first()

            if student:
                logger.info(f"Found matching student: {student.username}")
                
                # Get current active units for the student
                enrollments = self.db.query(Enrollment).filter(
                    Enrollment.user_id == student.id
                ).all()
                
                if not enrollments:
                    logger.warning(f"Student {student.username} has no active enrollments")
                    return

                # Create attendance records for each enrolled unit
                for enrollment in enrollments:
                    # Check if attendance already marked for today
                    existing_attendance = self.db.query(Attendance).filter(
                        Attendance.user_id == student.id,
                        Attendance.unit_id == enrollment.unit_id,
                        Attendance.marked_at >= datetime.utcnow().date()
                    ).first()
                    
                    if existing_attendance:
                        logger.info(f"Attendance already marked for student {student.username} in unit {enrollment.unit_id}")
                        continue
                    
                    attendance = Attendance(
                        user_id=student.id,
                        unit_id=enrollment.unit_id,
                        attendance_type=AttendanceType.BLUETOOTH,
                        bluetooth_address=address
                    )
                    self.db.add(attendance)
                    logger.info(f"Created attendance record for student {student.username} in unit {enrollment.unit_id}")
                
                self.db.commit()
                logger.info(f"Successfully processed attendance for student {student.username}")
            else:
                logger.debug(f"No matching student found for device: {address}")
                
        except Exception as e:
            logger.error(f"Error processing device {address}: {str(e)}")
            logger.error(traceback.format_exc())
            self.db.rollback()

    async def cleanup_old_devices(self):
        """Remove devices that haven't been seen for more than 5 minutes"""
        while self.scanning:
            try:
                current_time = datetime.utcnow()
                old_devices = [
                    address for address, last_seen in self.detected_devices.items()
                    if (current_time - last_seen).total_seconds() > 300  # 5 minutes
                ]
                for address in old_devices:
                    del self.detected_devices[address]
                    logger.debug(f"Removed old device: {address}")
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup_old_devices: {str(e)}")
                logger.error(traceback.format_exc())
                await asyncio.sleep(60)  # Continue checking even if there's an error

    async def start_scanning(self, broadcast_info: dict):
        """Start scanning for Bluetooth devices with specific broadcast info"""
        if self.scanning:
            logger.warning("Scanner is already running")
            return

        self.active_broadcast = broadcast_info
        self.scanning = True
        self.start_time = datetime.utcnow()
        logger.info(f"Starting Bluetooth scanner for unit {broadcast_info['unit_code']}")

        try:
            # Start the cleanup task
            self.cleanup_task = asyncio.create_task(self.cleanup_old_devices())
            
            # Start scanning
            self.scanner = BleakScanner(detection_callback=self.device_detection_callback)
            await self.scanner.start()
            logger.info("Bluetooth scanner started successfully")
        except Exception as e:
            logger.error(f"Error in Bluetooth scanner: {str(e)}")
            logger.error(traceback.format_exc())
            self.scanning = False
            raise

    async def stop_scanning(self):
        """Stop scanning for Bluetooth devices"""
        self.scanning = False
        self.active_broadcast = None
        self.detected_devices.clear()
        logger.info("Stopped Bluetooth scanner")
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.last_error = str(e)
                logger.error(f"Error stopping cleanup task: {str(e)}")
            self.cleanup_task = None
            
        if self.scanner:
            try:
                await self.scanner.stop()
            except Exception as e:
                self.last_error = str(e)
                logger.error(f"Error stopping scanner: {str(e)}")
            self.scanner = None
            
        logger.info("Bluetooth scanner stopped")

    def __del__(self):
        """Cleanup when the scanner is destroyed"""
        if self.scanning:
            asyncio.create_task(self.stop_scanning())
        if self.db:
            self.db.close()

    def detection_callback(self, device, advertisement_data):
        """Callback for when a Bluetooth device is detected"""
        if not self.scanning or not self.active_broadcast:
            return

        try:
            # Check if the device name matches our broadcast format
            device_name = advertisement_data.local_name
            if device_name and device_name.startswith("STUDENT_"):
                # Extract student ID from device name
                student_id = device_name.split("_")[1]
                self.detected_devices[student_id] = datetime.utcnow()
                logger.info(f"Detected student device: {device_name}")
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error in detection callback: {str(e)}")

    def is_device_detected(self, device_id: str) -> bool:
        """Check if a device has been detected recently"""
        if device_id not in self.detected_devices:
            return False
        
        # Consider device as detected if seen within last 5 minutes
        last_seen = self.detected_devices[device_id]
        return (datetime.utcnow() - last_seen).total_seconds() < 300

# Create a global scanner instance
scanner = BluetoothScanner()

async def start_scanner(broadcast_info: dict):
    """Start the Bluetooth scanner with broadcast info"""
    await scanner.start_scanning(broadcast_info)

async def stop_scanner():
    """Stop the Bluetooth scanner"""
    await scanner.stop_scanning() 