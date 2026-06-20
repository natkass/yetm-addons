from odoo import models, fields
import logging
import uuid
import os

class PosDownLoadWizard(models.TransientModel):
    _name="pos.log.download"
    
    password = fields.Char("Password")
    
    def action_confirm(self):
        logging.info(self.password)
        log_model_data = self.env["logging.event.model"].search([])

        if self.password == "1234":
            filename = "LOG [ETTAPOS] -" + uuid.uuid4().hex + ".txt"
            logging.info(f"logging info: creating record")
            module_directory_path = os.path.dirname(os.path.abspath(__file__))
            parent_directory = os.path.dirname(module_directory_path)
            logs_directory_path = os.path.join(parent_directory, 'logs')

            if not os.path.exists(logs_directory_path):
                os.makedirs(logs_directory_path)
                logging.info(f"Created logs directory at: {logs_directory_path}")
            else:
                logging.info(f"Logs directory already exists at: {logs_directory_path}")

            filepath = os.path.join(logs_directory_path, filename)
            logging.info(f"Module directory path: {module_directory_path}")
            logging.info(f"File path: {filepath}")

            logging.info(f"Type of log_model_data: {type(log_model_data)}")

            try:
                if log_model_data:
                    with open(filepath, "w") as f:
                        logs = "\n".join(f"{log.timestamp.strftime('%Y-%m-%d %H:%M:%S')} {log.log}" for log in log_model_data)
                        logging.info(f"Logging info: {logs}")
                        f.write(logs)
                    logging.info("Calling controller")
                else:
                    logging.warning("No log data found.")
            except Exception as e:
                logging.error(f"Error occurred while writing to file: {e}")
                return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'type': 'danger', 'title': 'Error', 'message': 'Failed to create log file.'}}

            return {
                'type': 'ir.actions.act_url',
                'url': f'/download/logfile?filepath={filepath}',
                'target': 'self'
            }

        return {'type': 'ir.actions.act_window_close'}