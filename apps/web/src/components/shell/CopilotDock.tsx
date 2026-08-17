import { Box, Button, InputBase, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import { copilotActions, copilotThread } from "../../features/dashboard/mockData";

export function CopilotDock() {
  return (
    <Box
      className="ufme-copilot"
      sx={{
        bgcolor: "background.paper",
        borderLeft: "1px solid",
        borderColor: "divider",
        display: "flex",
        flexDirection: "column",
        p: 2,
        minHeight: 0,
      }}
    >
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ pb: 1.5, borderBottom: "1px solid", borderColor: "divider" }}
      >
        <Typography sx={{ fontSize: 14, fontWeight: 700, color: "primary.main" }}>Copilot Assistant</Typography>
        <Box
          sx={{
            fontSize: 10,
            fontWeight: 700,
            px: 1,
            py: 0.35,
            borderRadius: 10,
            bgcolor: "var(--emerald-soft)",
            color: "success.main",
            border: "1px solid rgba(5,150,105,0.3)",
          }}
        >
          GPT-4 Financial Tuned
        </Box>
      </Stack>

      <Box sx={{ py: 1.5, borderBottom: "1px solid", borderColor: "divider" }}>
        <Typography sx={{ fontSize: 11, fontWeight: 700, mb: 0.75 }}>Recommended Actions</Typography>
        <Typography sx={{ fontSize: 11, color: "success.main", fontWeight: 700, mb: 1 }}>
          Estimated benefit: +$210M reduction
        </Typography>
        <Stack spacing={0.75}>
          {copilotActions.map((action) => (
            <Button
              key={action.label}
              component={RouterLink}
              to={action.to}
              size="small"
              variant="outlined"
              sx={{ justifyContent: "flex-start", fontSize: 11 }}
            >
              {action.label}
            </Button>
          ))}
        </Stack>
      </Box>

      <Stack spacing={1.5} sx={{ flex: 1, overflow: "auto", py: 1.75 }}>
        {copilotThread.map((message, index) => (
          <Box
            key={index}
            sx={{
              p: 1.5,
              borderRadius: 1,
              fontSize: 12,
              lineHeight: 1.5,
              maxWidth: "92%",
              alignSelf: message.role === "user" ? "flex-end" : "flex-start",
              bgcolor: message.role === "user" ? "var(--bg-muted)" : "var(--indigo-soft)",
              color: "text.primary",
            }}
          >
            {message.text}
          </Box>
        ))}
      </Stack>

      <Box sx={{ pt: 1.5, borderTop: "1px solid", borderColor: "divider" }}>
        <InputBase
          fullWidth
          placeholder="Ask Copilot or command agents (e.g. 'Explain EX-8902')..."
          sx={{
            fontSize: 12,
            px: 1.5,
            py: 1,
            bgcolor: "var(--bg-muted)",
            border: "1px solid",
            borderColor: "divider",
            borderRadius: 1,
          }}
        />
      </Box>
    </Box>
  );
}
