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
        
        # Migration: Add new columns if they don't exist (for v1.2)
        try:
            cursor.execute("ALTER TABLE tickets ADD COLUMN claimed_by TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE tickets ADD COLUMN claimed_at TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE tickets ADD COLUMN close_reason TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Initialize guild_config table (for v1.3)
        self.init_guild_config_table()
        
        conn.commit()
        conn.close()
    
    def init_guild_config_table(self):
        """Initialize the guild_config table for storing per-guild settings."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id TEXT PRIMARY KEY,
                panel_channel_id TEXT NOT NULL,
                support_role_id TEXT,
                ticket_category_id TEXT,
                ping_role_id TEXT,
                panel_title TEXT,
                panel_description TEXT,
                updated_at TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_guild_config(self, guild_id: str, config_dict: dict) -> bool:
        """Save or update guild configuration.
        
        Args:
            guild_id: Discord guild ID
            config_dict: Dictionary with configuration values
            
        Returns:
            True if saved successfully
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        updated_at = datetime.datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT OR REPLACE INTO guild_config 
            (guild_id, panel_channel_id, support_role_id, ticket_category_id, 
             ping_role_id, panel_title, panel_description, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(guild_id),
            str(config_dict.get('panel_channel_id', '')),
            str(config_dict.get('support_role_id', '')) if config_dict.get('support_role_id') else None,
            str(config_dict.get('ticket_category_id', '')) if config_dict.get('ticket_category_id') else None,
            str(config_dict.get('ping_role_id', '')) if config_dict.get('ping_role_id') else None,
            config_dict.get('panel_title'),
            config_dict.get('panel_description'),
            updated_at
        ))
        
        conn.commit()
        conn.close()
        return True
    
    def get_guild_config(self, guild_id: str) -> Optional[Dict]:
        """Get guild configuration.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Dictionary with configuration or None if not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM guild_config WHERE guild_id = ?
        """, (str(guild_id),))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def delete_guild_config(self, guild_id: str) -> bool:
        """Delete guild configuration.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            True if deleted successfully
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM guild_config WHERE guild_id = ?
        """, (str(guild_id),))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
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
    
    def close_ticket(self, channel_id: str, reason: str = None) -> bool:
        """Close a ticket by channel ID.
        
        Args:
            channel_id: Discord channel ID
            reason: Optional reason for closing the ticket
            
        Returns:
            True if ticket was closed, False if not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        closed_at = datetime.datetime.utcnow().isoformat()
        
        cursor.execute("""
            UPDATE tickets
            SET status = 'closed', closed_at = ?, close_reason = ?
            WHERE channel_id = ? AND status = 'open'
        """, (closed_at, reason, str(channel_id)))
        
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
    
    def claim_ticket(self, channel_id: str, user_id: str) -> bool:
        """Claim a ticket by channel ID.
        
        Args:
            channel_id: Discord channel ID
            user_id: Discord user ID of the staff member claiming the ticket
            
        Returns:
            True if ticket was claimed, False if not found or already claimed
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if ticket exists and is open
        ticket = self.get_ticket_by_channel(channel_id)
        if not ticket or ticket['status'] != 'open' or ticket.get('claimed_by'):
            conn.close()
            return False
        
        claimed_at = datetime.datetime.utcnow().isoformat()
        
        cursor.execute("""
            UPDATE tickets
            SET claimed_by = ?, claimed_at = ?
            WHERE channel_id = ? AND status = 'open' AND claimed_by IS NULL
        """, (str(user_id), claimed_at, str(channel_id)))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def unclaim_ticket(self, channel_id: str) -> bool:
        """Unclaim a ticket by channel ID.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            True if ticket was unclaimed, False if not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE tickets
            SET claimed_by = NULL, claimed_at = NULL
            WHERE channel_id = ? AND status = 'open'
        """, (str(channel_id),))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def get_claimed_tickets(self, user_id: str) -> List[Dict]:
        """Get all tickets claimed by a user.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            List of ticket dictionaries
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM tickets 
            WHERE claimed_by = ? AND status = 'open'
            ORDER BY claimed_at DESC
        """, (str(user_id),))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_ticket_statistics(self) -> Dict:
        """Get overall ticket statistics.
        
        Returns:
            Dictionary with statistics
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Total tickets
        cursor.execute("SELECT COUNT(*) as count FROM tickets")
        total = cursor.fetchone()['count']
        
        # Open tickets
        cursor.execute("SELECT COUNT(*) as count FROM tickets WHERE status = 'open'")
        open_count = cursor.fetchone()['count']
        
        # Closed tickets
        cursor.execute("SELECT COUNT(*) as count FROM tickets WHERE status = 'closed'")
        closed_count = cursor.fetchone()['count']
        
        # Claimed tickets
        cursor.execute("SELECT COUNT(*) as count FROM tickets WHERE status = 'open' AND claimed_by IS NOT NULL")
        claimed_count = cursor.fetchone()['count']
        
        # Unclaimed tickets
        cursor.execute("SELECT COUNT(*) as count FROM tickets WHERE status = 'open' AND claimed_by IS NULL")
        unclaimed_count = cursor.fetchone()['count']
        
        conn.close()
        
        return {
            'total': total,
            'open': open_count,
            'closed': closed_count,
            'claimed': claimed_count,
            'unclaimed': unclaimed_count
        }
    
    def get_tickets_by_period(self, days: int) -> Dict:
        """Get tickets created in the last N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with period statistics
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat()
        
        # Total in period
        cursor.execute("""
            SELECT COUNT(*) as count FROM tickets 
            WHERE created_at >= ?
        """, (cutoff_date,))
        total = cursor.fetchone()['count']
        
        # Open in period
        cursor.execute("""
            SELECT COUNT(*) as count FROM tickets 
            WHERE created_at >= ? AND status = 'open'
        """, (cutoff_date,))
        open_count = cursor.fetchone()['count']
        
        # Closed in period
        cursor.execute("""
            SELECT COUNT(*) as count FROM tickets 
            WHERE created_at >= ? AND status = 'closed'
        """, (cutoff_date,))
        closed_count = cursor.fetchone()['count']
        
        conn.close()
        
        return {
            'total': total,
            'open': open_count,
            'closed': closed_count
        }

