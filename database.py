"""SQLite database operations for ticket management."""
import sqlite3
import datetime
from typing import Optional, List, Dict
from config import Config


class TicketDatabase:
    """Handles all database operations for tickets."""
    
    def __init__(self, db_path: str = None):
        """Initialize database connection and create tables if needed."""
        self.db_path = db_path or Config.DATABASE_PATH
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize the database and create tables if they don't exist."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                closed_at TEXT,
                status TEXT NOT NULL DEFAULT 'open'
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_ticket(self, channel_id: str, user_id: str) -> int:
        """Create a new ticket in the database.
        
        Args:
            channel_id: Discord channel ID
            user_id: Discord user ID who created the ticket
            
        Returns:
            The ticket_id of the created ticket
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        created_at = datetime.datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT INTO tickets (channel_id, user_id, created_at, status)
            VALUES (?, ?, ?, 'open')
        """, (str(channel_id), str(user_id), created_at))
        
        ticket_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return ticket_id
    
    def close_ticket(self, channel_id: str) -> bool:
        """Close a ticket by channel ID.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            True if ticket was closed, False if not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        closed_at = datetime.datetime.utcnow().isoformat()
        
        cursor.execute("""
            UPDATE tickets
            SET status = 'closed', closed_at = ?
            WHERE channel_id = ? AND status = 'open'
        """, (closed_at, str(channel_id)))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def get_ticket_by_channel(self, channel_id: str) -> Optional[Dict]:
        """Get ticket information by channel ID.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            Dictionary with ticket data or None if not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM tickets WHERE channel_id = ?
        """, (str(channel_id),))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_user_tickets(self, user_id: str, status: str = None) -> List[Dict]:
        """Get all tickets for a user.
        
        Args:
            user_id: Discord user ID
            status: Optional status filter ('open' or 'closed')
            
        Returns:
            List of ticket dictionaries
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute("""
                SELECT * FROM tickets 
                WHERE user_id = ? AND status = ?
                ORDER BY created_at DESC
            """, (str(user_id), status))
        else:
            cursor.execute("""
                SELECT * FROM tickets 
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (str(user_id),))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def is_ticket_channel(self, channel_id: str) -> bool:
        """Check if a channel is a ticket channel.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            True if channel is a ticket channel
        """
        ticket = self.get_ticket_by_channel(channel_id)
        return ticket is not None

