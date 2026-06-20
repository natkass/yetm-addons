##############################################################################
#
#    Copyright Domiup (<http://domiup.com>).
#
##############################################################################

from .base_configuration import ApprovalTestConfiguration


class ApprovalNextMoveTest(ApprovalTestConfiguration):
    def test_request_approval(self):
        # Request approval
        request1 = self.request_one(self.obj_1, self.user_1)
        self.assertEqual(request1.type_id, self.approval_type_2)
        # To trigger type_3
        self.approval_type_2.approve_python_code = (
            'record.write({"state": "to_approve_2"})'
        )
        self.approval_type_2.next_move_ids = self.approval_type_3

        # Approve Request
        request1.with_user(self.approver_1).action_approve()
        request1.with_user(self.approver_2).action_approve()
        self.assertEqual(request1.state, "Approved")
        self.assertEqual(request1.origin_ref.state, "to_approve_2")
        self.assertTrue(request1.origin_ref.x_need_approval)
        self.assertFalse(request1.origin_ref.x_review_result)

        # New request
        origin_ref = f"{request1.origin_ref._name},{request1.origin_ref.id}"
        request2 = self.env[request1._name].search(
            [
                ("origin_ref", "=", origin_ref),
                ("type_id", "=", self.approval_type_3.id),
                ("state", "=", "Submitted"),
            ]
        )
        self.assertEqual(len(request2), 1)

        # Approve Request again
        request2.with_user(self.approver_1).action_approve()
        request2.with_user(self.approver_2).action_approve()
        self.assertEqual(request2.state, "Approved")
        self.assertEqual(request2.origin_ref.state, "approve")
        self.assertEqual(request2.origin_ref.x_review_result, "approved")
