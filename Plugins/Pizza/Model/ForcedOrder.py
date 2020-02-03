from Plugins.Pizza.Model.Order import Order


class ForcedOrder(Order):
    def with_order(self, order: Order):
        self.chat_id = order.chat_id
        self.user_id = order.user_id
        self.user_name = order.user_name
        return self
